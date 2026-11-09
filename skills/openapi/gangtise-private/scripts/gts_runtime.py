"""Gangtise OpenAPI 运行时（skill 独立运行版）：错误类型、信封解析、请求重试、表格展开、时间换算、Result。

每个 skill 的 scripts/gts_runtime.py 必须逐字节相同，由 scripts/check_skills.py 校验。
CLI / MCP 同步时，`from .gts_runtime import` 会被改写为 `from gangtise_core.skill_runtime import`，
因此 __all__ 里的名字必须在 core/src/gangtise_core/skill_runtime.py 中同名存在；
ERROR_HINTS、PARAM_CODES、ENDPOINT_POLICIES、ROW_BILLING_PRICES 也由校验脚本与 core 比对。
"""
from __future__ import annotations

import contextvars
import datetime
import email.utils
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor as _ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Pattern, Sequence

import requests

from .gts_auth import authorized_request

__all__ = [
    "ApiError",
    "GangtiseError",
    "PartialResultError",
    "Result",
    "SavedFile",
    "StructuralError",
    "ThreadPoolExecutor",
    "ValidationError",
    "failure_result",
    "credit_guard_enabled",
    "guard_row_billed_fetch",
    "maybe_timestamp13",
    "records_from_block",
    "records_from_envelope_body",
    "request_json",
    "success_result",
    "to_timestamp13",
    "unwrap",
    "zip_field_row",
    "zip_field_rows",
]


# ── 并发 ──

class ThreadPoolExecutor(_ThreadPoolExecutor):
    """工作线程继承提交时的 contextvars（CLI / MCP 侧的请求级鉴权、域名透传依赖它）。"""

    def submit(self, fn, /, *args, **kwargs):
        # 每个任务单独 copy：同一 Context 不能被多个线程同时 run
        ctx = contextvars.copy_context()
        return super().submit(ctx.run, fn, *args, **kwargs)


# ── 错误码提示 ──

ERROR_HINTS: Dict[str, str] = {
    # ── 服务统一层 999xxx ──
    "999001": "检查 GTS_ACCESS_KEY / GTS_SECRET_KEY 是否已配置（gangtise configure --show）。",
    "999002": "有 AK/SK 时会自动重新登录重试一次，否则请重新 gangtise configure。",
    "999003": "定制接口需联系客户经理开通。",
    "999004": "整库/整接口未开通（如帕米尔专家纪要需单独购买），或该条记录本账号不可见——list 撞上多为前者，先确认该数据库是否已开通。",
    "999005": "联系客户经理充值，或缩小查询范围降低消耗。",
    "999006": "触发限流，稍后再试或联系客户经理提额；429 所有端点都退避重试，5xx 仅普通端点重试（计费 no-replay 端点的 5xx 不重放，但其 429 仍重试）。",
    "999007": "请求方法不支持——直调接口时确认该 endpoint 是 GET 还是 POST。",
    "999008": "Content-Type 不支持，该接口只收 application/json。",
    "999009": "请求体无法解析，检查 JSON 是否合法。",
    "999010": "接口地址可能已下线，确认使用的是最新版本。",
    "999011": "检查 GTS_ACCESS_KEY / GTS_SECRET_KEY 是否写反或未配置。",
    "999012": "联系客户经理。",
    "999013": "联系客户经理续期。",
    "999014": "联系客户经理。",
    "999015": "联系客户经理开通长期 token。",
    "999016": "联系客户经理登记当前出口 IP。",
    "999999": "请稍后重试；持续失败请带上面的 trace 报障。",
    # ── 业务通用 1xxxxx ──
    "100001": "对照命令 --help 检查必填项。",
    "100002": "检查数值/字符串参数是否传反。",
    "100003": "msg 已指明字段名或取值范围时直接按 msg 改；msg 只说「参数值非法」时多为枚举参数拼写错误，对照命令 --help 列出的合法值检查。",
    "100004": "检查 --page-size / --page-from 是否为非负数且未超单页上限。",
    "100005": "对照命令 --help 列出的合法取值检查。",
    "100006": "缩短日期范围或调小 --limit（list 类端点单页上限为 50）；指标截面 / 时序撞此码是单次单元格数超 30000（截面=证券数×指标数，时序=证券数或指标数×日期数），按这个乘积拆批重跑。",
    "110001": "看参数名：`--*-date` 用 YYYY-MM-DD，`--*-time` 用 \"YYYY-MM-DD HH:mm:ss\"。",
    "110002": "起始晚于结束——检查 --start-date/--end-date 或 --start-time/--end-time 的先后。",
    "110003": "查询时间超出本账号的数据权限范围——把日期移进范围内（整个区间都早于下界时缩短窗口无用），或联系客户经理开通更长历史。",
    "120001": "用 `gangtise security -k <名称>` 确认代码与后缀（如 600519.SH / 00700.HK）。",
    "130001": "未找到数据——先核对查询条件；指标端点此码也可能是未开通该指标权限，仍失败联系客户经理。",
    "130002": "确认 ID 有效且本账号可见（删除类操作收到此码可能是目标已被删掉）；下载类还需检查文件类型取值是否合法。",
    "130003": "资源未生成或该条记录未附带文件——换一条有附件的记录，或稍后再试。",
    "130004": "下载 ID 需为数字，检查该命令的 --*-id 参数是否传对。",
    "130005": "对照命令 --help 检查文件类型 / 内容类型取值。",
    "140001": "异步任务仍在生成，稍后用同一 job 再查。",
    "140002": "终态失败，立即重试同一请求不会变。msg 指向参数（指标参数名/枚举以 company_indicator 搜索返回的 parameterList 为准）就改参数重新提交；msg 是「业务处理失败」则与参数无关，稍后再试，持续出现请带 trace 报障。",
    # ── 接口专有 2xxxxx ──
    "210001": "换一篇，或改用 list 取正文摘要。",
    "220001": "改用 list 取正文摘要。",
    "230001": "只有自己上传的文件可下载。",
    "230002": "微信账号未绑定——群消息类接口要求先在 Gangtise 端绑定并激活群消息助理、且助理已入群。",
    "230003": "股票池数量已达账号上限（30 个）——先删掉不用的池再建。",
    "230004": "云盘文件 / 文件夹名称超过 200 个字符（按 UTF-16 计，中文算 1、emoji 算 2）——缩短后重试。",
    "230005": "文件夹不能移到自身、自己的子文件夹或另一个空间——换一个同空间、不在其下级的目标文件夹。",
    "230006": "池名与该账号已有的池重复——先用 `gangtise stockpool` 查看现有名称，换一个再建/改名。",
    "230007": "池名超过 10 个字符（按字符计，中文算 1 个）——缩短后重试。",
    "230008": "试用账号当日累计上传已超过 500MB——次日再传，或联系客户经理。",
    "240001": "换更早的报告期（如 2025q3 → 2025interim）。",
    "240002": "改述后重新提交。",
    "240003": "对照命令 --help 检查取值。",
    "250001": "检查 resourceType 与 sourceId 组合（两者都来自知识库检索返回）。",
    # ── 旧码（一部分仍在线，一部分已被取代）──
    "0000001007": "请求未携带 Bearer token，检查 AK/SK 是否已配置。",
    "0000001008": "Token 已失效（多为他处登录挤掉本会话）；有 AK/SK 时会自动重新登录重试一次，否则请重新登录。",
    "900001": "对照命令 --help 检查必填项。",
    "900002": "请求方法不正确（服务端 msg 为「请求类型有误」）——检查该 endpoint 是 GET 还是 POST。",
    "903301": "次日再试，或联系客户经理提额。",
    "410001": "补齐指标与证券；时序不支持「多指标 × 多证券」，改用截面查询。",
    "410106": "读 company_indicator 搜索返回的 parameterList，在 params 里补上 required:true 的参数（如 periodNum / sDate / fiscalYear）。",
    "410004": "换证券或日期确认该条件下本应有数据；仍失败多为未开通该指标，联系客户经理。",
    "410110": "异步任务仍在生成，稍后用同一 job 再查。",
    "410111": "终态，换参数后重新提交，重试同一请求不会变。",
    "430004": "确认 reportId 有效，或更换文件类型重试（官方未文档化错误码）。",
    "430007": "缩短日期范围或调小 --limit。",
    "433007": "检查 resourceType 与 sourceId 组合（两者都来自知识库检索返回）。",
    "8000014": "检查 GTS_ACCESS_KEY 是否正确、是否与 SECRET_KEY 写反。",
    "8000015": "检查 GTS_SECRET_KEY 是否正确、是否与 ACCESS_KEY 写反。",
    "8000016": "联系客户经理核查账号状态。",
    "8000018": "联系客户经理续期。",
    "999995": "联系客户经理充值，或缩小查询范围降低消耗。",
    "999997": "联系客户经理开通。",
    "10011401": "联系客户经理开通白名单。",
}

_CLAUSE = re.compile(r"指标\s+(\S+)\s+(不支持参数|缺少必填参数)[:：]?\s*(\S+)")


def _distinct_failure_shapes(message: str) -> int:
    by_code: Dict[str, set] = {}
    for clause in re.split(r"[;；]", message or ""):
        m = _CLAUSE.search(clause)
        if not m:
            continue
        code, kind, key = m.groups()
        by_code.setdefault(code, set()).add(f"{kind}:{key}")
    if not by_code:
        return 1
    return len({"|".join(sorted(shape)) for shape in by_code.values()})


@dataclass(frozen=True)
class _MessageRule:
    codes: tuple
    match: Pattern[str]
    hint: str
    also: Optional[Pattern[str]] = None
    not_match: Optional[Pattern[str]] = None
    when: Optional[Callable[[str], bool]] = None

    def applies(self, code: str, message: str) -> bool:
        return (
            code in self.codes
            and bool(self.match.search(message))
            and (self.also is None or bool(self.also.search(message)))
            and not (self.not_match is not None and self.not_match.search(message))
            and (self.when is None or self.when(message))
        )


def _single(message: str) -> bool:
    return _distinct_failure_shapes(message) <= 1


def _batch(message: str) -> bool:
    return _distinct_failure_shapes(message) > 1


_EDE = ("100001", "100003")

MESSAGE_HINTS: List[_MessageRule] = [
    _MessageRule(
        codes=_EDE,
        match=re.compile(r"不支持参数\s*(?:tradeDate|reportDate)|缺少必填参数[:：]?\s*(?:tradeDate|reportDate)"),
        when=_batch,
        hint=(
            "这条报错涉及多个指标，而且它们失败的方式不同——同一个改法套不到全部，按 msg 里每个指标各自说的话分别处理："
            "「不支持参数 X; 缺少必填参数 Y」= 在 params 里把该指标的 X 换成 Y；只说「不支持参数 X」= 该指标一个日期都不要，"
            "给它传空参数 {\"<指标code>\": {}}；只说「缺少必填参数 Y」= 补上 Y。最省事的办法是把这批指标拆成几次单独查。"
            "以 company_indicator 搜索返回的 parameterList 为准。"
        ),
    ),
    _MessageRule(
        codes=_EDE,
        match=re.compile(r"缺少必填参数[:：]?\s*reportDate"),
        when=_single,
        hint=(
            "报错点名的指标要的是 reportDate（报告期），不是按日期下发的 tradeDate。在 params 里给每个被点名的指标补 "
            "{\"<指标code>\": {\"reportDate\": \"YYYY-MM-DD\"}}。少数指标两个日期都要（如 div_cash_yld），补完若再报缺 tradeDate，"
            "就把 tradeDate 也显式传上。以 parameterList 为准，别按 code 前缀推断。"
        ),
    ),
    _MessageRule(
        codes=_EDE,
        match=re.compile(r"不支持参数\s*(?:tradeDate|reportDate)"),
        also=re.compile(r"缺少必填参数[:：]?\s*tradeDate"),
        when=_single,
        hint=(
            "服务端在同一句里已经点名了两边：一个键不该出现，另一个键缺了——把前者换成后者即可。多半是两个日期键写反了："
            "删掉 params 里被拒的那个，改成 msg 里说缺的那个（如 {\"<指标code>\": {\"tradeDate\": \"YYYY-MM-DD\"}}）。"
            "别在这一步传空参数——服务端明说了它要一个日期。"
        ),
    ),
    _MessageRule(
        codes=_EDE,
        match=re.compile(r"不支持参数\s*(?:tradeDate|reportDate)"),
        not_match=re.compile(r"缺少必填参数[:：]?\s*(?:reportDate|tradeDate)"),
        when=_single,
        hint=(
            "服务端只说这个键不该出现，没说该换成哪个——别照着「改用 reportDate」做，那多半同样被拒。给被点名的指标传空参数 "
            "{\"<指标code>\": {}} 声明「本指标不要查询日期」；再看 parameterList 是否还列了 fiscalYear 之类的必填项，一并补上。"
        ),
    ),
    _MessageRule(
        codes=_EDE,
        match=re.compile(r"缺少必填参数[:：]?\s*tradeDate"),
        when=_single,
        hint=(
            "tradeDate 这次没有下发——你为该指标显式传了 reportDate/tradeDate 或空参数，都会关掉自动注入。"
            "若该指标两个日期都必填（如 div_cash_yld），把 tradeDate 也显式传上；若空参数加错了指标，删掉它即可。"
        ),
    ),
]


def hint_for(code: Optional[str], message: str = "") -> Optional[str]:
    code = str(code or "")
    if not code:
        return None
    for rule in MESSAGE_HINTS:
        if rule.applies(code, message or ""):
            return rule.hint
    return ERROR_HINTS.get(code)


# ── 错误类型 ──

PARAM_CODES = frozenset(
    {
        "100001", "100002", "100003", "100004", "100005", "100006",
        "110001", "110002", "120001", "130004", "130005", "140002",
        "240003", "900001",
    }
)


class GangtiseError(Exception):
    """`exit_code`：1 失败、2 参数错误、3 部分成功。"""

    exit_code = 1

    def __init__(self, message: str, *, code: str = "", trace_id: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.code = str(code or "")
        self.trace_id = str(trace_id or "")

    def __str__(self) -> str:
        parts = [self.message]
        if self.code:
            parts.append(f"code={self.code}")
        if self.trace_id:
            parts.append(f"traceId={self.trace_id}")
        return " ".join(parts)


class ValidationError(GangtiseError):
    """本地拒绝的参数，请求未发出、不计费。"""

    exit_code = 2

    def __str__(self) -> str:
        return self.message


def _trace_from_body(body: Any) -> str:
    if isinstance(body, dict):
        value = body.get("traceId") or body.get("_traceId") or body.get("trace_id")
        if isinstance(value, (str, int)) and not isinstance(value, bool) and str(value):
            return str(value)
    return ""


class ApiError(GangtiseError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "",
        http: int = 0,
        trace_id: str = "",
        body: Optional[Any] = None,
        retry_after_ms: Optional[int] = None,
        hint: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code, trace_id=str(trace_id or "") or _trace_from_body(body))
        self.http = int(http or 0)
        self.body = body
        self.retry_after_ms = retry_after_ms
        self.hint = hint if hint is not None else hint_for(self.code, message)
        if self.code in PARAM_CODES or (400 <= self.http < 500 and self.http not in {401, 403, 429}):
            self.exit_code = 2

    def __str__(self) -> str:
        head = f"API error ({self.code})" if self.code else "API error"
        if self.trace_id:
            head += f" [trace {self.trace_id}]"
        msg = self.message
        if self.http >= 400 and "HTTP" not in msg:
            msg = f"{msg} (HTTP {self.http})"
        return f"{head}: {msg}" + (f" {self.hint}" if self.hint else "")


class StructuralError(GangtiseError):
    """返回结构无法安全使用（fieldList 与行不等宽、列名重复等）。"""


class PartialResultError(GangtiseError):
    exit_code = 3


# ── 信封 ──

OK_CODES = frozenset({"000000", "0", "200", ""})


def _is_ok(body: Mapping[str, Any], *, http: int = 200) -> bool:
    if http and http >= 400:
        return False
    if body.get("status") is False or body.get("state") is False or body.get("success") is False:
        return False
    code = str(body.get("code", "")).strip()
    if code and code not in OK_CODES:
        return False
    if body.get("status") is True or body.get("state") is True or body.get("success") is True:
        return True
    if code in OK_CODES:
        return True
    return "data" in body


def unwrap(body: Any, *, http: int = 200, expect_data: bool = True) -> Any:
    """返回 `data`（无信封时返回整体）；失败抛 ApiError。"""
    if not isinstance(body, dict):
        if http and http >= 400:
            raise ApiError(f"API request failed (HTTP {http})", http=http, body=body)
        if expect_data:
            raise ApiError("响应不是 JSON 对象", http=http)
        return body
    trace_id = str(body.get("traceId") or body.get("trace_id") or "")
    code = str(body.get("code", "")).strip()
    msg = str(body.get("msg") or body.get("message") or body.get("error") or "")
    if not _is_ok(body, http=http):
        if not msg and http and http >= 400:
            msg = f"API request failed (HTTP {http})"
        raise ApiError(msg or "API request failed", code=code, http=http, trace_id=trace_id, body=body)
    if "data" in body:
        data = body.get("data")
        if isinstance(data, dict) and "code" in data and str(data.get("code", "")) not in OK_CODES:
            inner_msg = str(data.get("msg") or data.get("message") or msg or "inner envelope failed")
            raise ApiError(inner_msg, code=str(data.get("code", "")), http=http, trace_id=trace_id, body=body)
        return data
    return body


# ── fieldList 表格 ──

def zip_field_row(fields: Sequence[str], row: Sequence[Any], *, trace_id: str = "") -> dict:
    if len(fields) != len(row):
        raise StructuralError(
            f"fieldList {len(fields)} 列，行 {len(row)} 个值，按位置对齐会错位，已拒绝输出",
            trace_id=trace_id,
        )
    dupes = [f for i, f in enumerate(fields) if f in fields[:i]]
    if dupes:
        raise StructuralError(f"响应 fieldList 有重复列名: {', '.join(sorted(set(dupes)))}", trace_id=trace_id)
    return {fields[i]: row[i] for i in range(len(fields))}


def zip_field_rows(fields: Sequence[str], rows: Iterable[Sequence[Any]], *, trace_id: str = "") -> List[dict]:
    return [zip_field_row(fields, row, trace_id=trace_id) for row in rows]


def records_from_block(block: Any, *, trace_id: str = "") -> List[Dict[str, Any]]:
    if block is None:
        return []
    if isinstance(block, list):
        if not block:
            return []
        if isinstance(block[0], dict):
            return [row for row in block if isinstance(row, dict)]
        raise StructuralError("响应包含数组形式的行但没有 fieldList，无法确定各列的含义，已拒绝输出", trace_id=trace_id)
    if not isinstance(block, dict):
        return []
    fields = block.get("fieldList") or block.get("fields")
    rows = block.get("list")
    if rows is None:
        rows = block.get("rows")
    if fields and rows is not None:
        seq = []
        for row in rows:
            if isinstance(row, (list, tuple)):
                seq.append(row)
            elif isinstance(row, dict):
                seq.append([row.get(f) for f in fields])
        return zip_field_rows(list(fields), seq, trace_id=trace_id)
    return []


def records_from_envelope_body(body: Any, *, http: int = 200) -> List[Dict[str, Any]]:
    """解信封后展开 fieldList 表格；空列表表示无数据（不是错误）。"""
    data = unwrap(body, http=http)
    trace_id = str(body.get("traceId") or body.get("trace_id") or "") if isinstance(body, dict) else ""
    return records_from_block(data, trace_id=trace_id)


def _fail_list_of(data: Any) -> Optional[list]:
    if isinstance(data, dict):
        fail = data.get("failList") or data.get("fail_list")
        if fail:
            return list(fail)
    return None


# ── 时间（按北京时间换算，只收年在前的写法）──

CST = datetime.timezone(datetime.timedelta(hours=8))
_LOCAL_DATETIME = re.compile(r"^(\d{4})([-/]?)(\d{2})\2(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$")
_YEAR_FIRST_DATE = re.compile(r"^(\d{4})([-/]?)(\d{2})\2(\d{2})$")
_YEAR_LAST_NOTE = (
    "year-last layouts are refused because the API reads them month-first (US convention): "
    '"01-07-2026" means 7 January, not 1 July'
)
_DATETIME_EXPECTED = (
    'expected a Unix timestamp or "YYYY-MM-DD" optionally with " HH:mm[:ss]" '
    "(space or T separator; YYYY/MM/DD and YYYYMMDD also accepted)"
)


def _fields_valid(year: int, month: int, day: int, hh: int = 0, mi: int = 0, ss: int = 0) -> bool:
    if not 1 <= month <= 12:
        return False
    leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    dim = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return 1 <= day <= dim and hh <= 23 and mi <= 59 and ss <= 59


def _epoch_millis(value: str) -> Optional[int]:
    if re.fullmatch(r"\d{13}", value):
        return int(value)
    if re.fullmatch(r"\d{10}", value):
        return int(value) * 1000
    return None


def to_timestamp13(day: Any, *, end_of_day: bool = False, option: str = "date") -> int:
    """时间戳 / 日期 / 日期时间 → 13 位毫秒（北京时间）。`end_of_day` 只对纯日期生效：取次日 0 点。"""
    s = str(day if day is not None else "").strip()
    ts = _epoch_millis(s)
    if ts is not None:
        return ts
    m = _LOCAL_DATETIME.match(s)
    parts = None
    if m:
        y, _sep, mo, d, hh, mi, ss = m.groups()
        parts = (int(y), int(mo), int(d), int(hh or 0), int(mi or 0), int(ss or 0))
        if not _fields_valid(*parts):
            parts = None
    if parts is None:
        raise ValidationError(f'Invalid {option}: {_DATETIME_EXPECTED}, got "{day}" — {_YEAR_LAST_NOTE}')
    dt = datetime.datetime(*parts, tzinfo=CST)
    if end_of_day and _YEAR_FIRST_DATE.match(s):
        dt += datetime.timedelta(days=1)
    return int(dt.timestamp() * 1000)


def maybe_timestamp13(day: Optional[Any], *, end_of_day: bool = False, option: str = "date") -> Optional[int]:
    if day is None or str(day).strip() == "":
        return None
    return to_timestamp13(day, end_of_day=end_of_day, option=option)


# ── Result ──

@dataclass
class SavedFile:
    path: str
    kind: str = "data"
    label: str = ""


@dataclass
class Result:
    ok: bool = True
    text: str = ""
    data: Any = None
    files: List[SavedFile] = field(default_factory=list)
    markers: Dict[str, str] = field(default_factory=dict)
    usage: Dict[str, Any] = field(default_factory=dict)
    error: Optional[GangtiseError] = None
    exit_code: int = 0
    tool: str = ""

    @classmethod
    def success(
        cls,
        text: str = "",
        *,
        data: Any = None,
        files: Optional[List[SavedFile]] = None,
        markers: Optional[Dict[str, str]] = None,
        usage: Optional[Dict[str, Any]] = None,
        tool: str = "",
    ) -> "Result":
        return cls(
            ok=True,
            text=text,
            data=data,
            files=list(files or []),
            markers=dict(markers or {}),
            usage=dict(usage or {}),
            tool=tool,
        )

    def __str__(self) -> str:
        if self.ok:
            return self.text or ""
        return self.text or str(self.error or "")


_EMPTY_HINTS = ("未找到", "无数据", "无证券", "无自选", "日期范围内未找到", "当前账号下无")
_PARAM_HINTS = (
    "仅支持", "不能为空", "无效:", "无效：", "请指定", "不要使用", "须为", "必须为", "已拒绝",
    "非法", "缺少必填参数", "超出限制", "参数类型错误", "必须且只能", "只能指定",
)


def failure_result(response: Dict[str, Any]) -> Result:
    """`{state: error}` 结果：无数据 → 空的成功结果；服务端错误码 / 参数 / 鉴权 → 抛 ApiError。"""
    msg = str(response.get("message") or response.get("msg") or "调用失败")
    code = str(response.get("code") or "")
    http = int(response.get("http") or 0)
    trace_id = str(response.get("traceId") or response.get("trace_id") or "")
    if code and code not in OK_CODES:
        raise ApiError(msg, code=code, http=http, trace_id=trace_id, body=response)
    if any(h in msg for h in _PARAM_HINTS):
        raise ApiError(msg, code="100003", http=http or 400, trace_id=trace_id, body=response)
    if "未配置" in msg and "授权" in msg:
        raise ApiError(msg, code="999011", http=http, trace_id=trace_id, body=response)
    if any(h in msg for h in _EMPTY_HINTS):
        return Result.success(text=msg, data=[])
    raise ApiError(msg, code=code, http=http, trace_id=trace_id, body=response)


def success_result(markdown: str, response: Dict[str, Any], *, files: Optional[List[SavedFile]] = None) -> Result:
    tables: List[Any] = []
    for item in response.get("data") or []:
        if isinstance(item, dict) and item.get("type") == "data":
            tables.append(item.get("data"))
    data: Any = None
    if len(tables) == 1:
        data = tables[0]
    elif tables:
        data = tables
    result = Result.success(
        text=(markdown or "").strip(),
        data=data,
        files=list(files or []),
        usage=dict(response.get("usage") or {}),
    )
    partial = response.get("partial")
    if partial:
        result.exit_code = PartialResultError.exit_code
        result.markers["partial"] = partial if isinstance(partial, str) else "true"
    return result


# ── 请求与重试 ──
# retry：默认对 429 / 5xx / 999999 / 网络错误重试；no-replay（计费或非幂等）只在 429 与连接阶段失败时重试；
# no-999999（EDE 指标）不重试 999999。item_failures：返回 000000 但带 failList 时按部分失败处理。
# 与 core/src/gangtise_core/data/endpoints.yaml 中非默认项一致，由 scripts/check_skills.py 校验。

ENDPOINT_POLICIES: Dict[str, Dict[str, Any]] = {
    "/bond/basic-info": {"retry": "no-replay"},
    "/bond/issuer-info": {"retry": "no-replay"},
    "/bond/daily-quote-exchange-cfets": {"retry": "no-replay"},
    "/bond/valuation-shclearing": {"retry": "no-replay"},
    "/bond/cash-flow": {"retry": "no-replay"},
    "/bond/announcement": {"retry": "no-replay"},
    "/bond/issuance-detail": {"retry": "no-replay"},
    "/bond/rating-overview": {"retry": "no-replay"},
    "/bond/rating-change": {"retry": "no-replay"},
    "/bond/issuer-rating-change": {"retry": "no-replay"},
    "/bond/issuance-plan": {"retry": "no-replay"},
    "/bond/exercise-notice": {"retry": "no-replay"},
    "/bond/default-list": {"retry": "no-replay"},
    "/EDE/search": {"retry": "no-999999"},
    "/EDE/time-series": {"retry": "no-999999"},
    "/EDE/cross-section": {"retry": "no-999999"},
    "/EDB/getData": {"retry": "no-replay"},
    "/screener": {"retry": "no-999999"},
    "/chief-opinion/getDetail": {"retry": "no-replay"},
    "/foreign-opinion/getDetail": {"retry": "no-replay"},
    "/summary/v2/download/file": {"retry": "no-replay"},
    "/broker-report/download/file": {"retry": "no-replay"},
    "/announcement/download/file": {"retry": "no-replay"},
    "/foreign-report/download/file": {"retry": "no-replay"},
    "/pamirs-summary/download/file": {"retry": "no-replay"},
    "/officialAccount/download/file": {"retry": "no-replay"},
    "/ai/resource/download": {"retry": "no-replay"},
    "/stock-pool/createPool": {"retry": "no-replay"},
    "/stock-pool/addStock": {"item_failures": True},
    "/stock-pool/deleteStock": {"item_failures": True},
    "/stock-pool/deletePool": {"retry": "no-replay", "item_failures": True},
    "/stock-pool/addNote": {"retry": "no-replay"},
    "/stock-pool/deleteNote": {"retry": "no-replay", "item_failures": True},
    "/my-conference/download/file": {"retry": "no-replay"},
    "/record/download/file": {"retry": "no-replay"},
    "/drive/download/file": {"retry": "no-replay"},
    "/drive/uploadFile": {"retry": "no-replay"},
    "/drive/createFolder": {"retry": "no-replay"},
    "/drive/moveFile": {"item_failures": True},
    "/drive/copy": {"retry": "no-replay", "item_failures": True},
    "/drive/deleteFile": {"retry": "no-replay", "item_failures": True},
    "/drive/deleteFolder": {"retry": "no-replay"},
}

TERMINAL_API_CODES = frozenset({"999011", "140002"})
RETRYABLE_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})
RETRY_AFTER_CEILING_MS = 60_000
DEFAULT_RETRIES = 2
BASE_DELAY_MS = 400
MAX_DELAY_MS = 4_000
_CONNECT_PHASE_MARKERS = (
    "NewConnectionError",
    "NameResolutionError",
    "Failed to resolve",
    "Name or service not known",
    "nodename nor servname",
    "Temporary failure in name resolution",
    "Connection refused",
)


def _endpoint_policy(url: str) -> Dict[str, Any]:
    u = str(url or "").split("?", 1)[0].rstrip("/")
    best: Dict[str, Any] = {}
    best_len = -1
    for path, policy in ENDPOINT_POLICIES.items():
        p = path.rstrip("/")
        if p and (u.endswith(p) or p in u) and len(p) > best_len:
            best, best_len = policy, len(p)
    return best


def _is_connect_phase(err: BaseException) -> bool:
    if isinstance(err, requests.exceptions.ConnectTimeout):
        return True
    if not isinstance(err, requests.exceptions.ConnectionError):
        return False
    seen = set()
    cur: Optional[BaseException] = err
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if any(m in f"{type(cur).__name__}: {cur}" for m in _CONNECT_PHASE_MARKERS):
            return True
        reason = getattr(cur, "reason", None)
        nxt = reason if isinstance(reason, BaseException) else None
        if nxt is None and cur.args and isinstance(cur.args[0], BaseException):
            nxt = cur.args[0]
        cur = nxt or cur.__cause__ or cur.__context__
    return False


def _is_retryable(err: BaseException, policy: str) -> bool:
    if isinstance(err, ApiError):
        if err.code in TERMINAL_API_CODES:
            return False
        if err.http == 429:
            return True
        if policy == "no-replay":
            return False
        if err.code == "999999":
            return policy != "no-999999"
        return err.http in RETRYABLE_HTTP_STATUS
    if isinstance(err, requests.exceptions.RequestException):
        if _is_connect_phase(err):
            return True
        if policy == "no-replay":
            return False
        return isinstance(
            err,
            (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ChunkedEncodingError),
        )
    return False


def _parse_retry_after_ms(value: Optional[str]) -> Optional[int]:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw) * 1000
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed is None:
        return None
    return max(0, int(parsed.timestamp() * 1000 - time.time() * 1000))


def _backoff_ms(attempt: int, err: BaseException) -> float:
    retry_after = getattr(err, "retry_after_ms", None)
    if isinstance(retry_after, (int, float)) and retry_after >= 0:
        return min(float(retry_after), RETRY_AFTER_CEILING_MS)
    return min(MAX_DELAY_MS, BASE_DELAY_MS * 2 ** attempt + random.random() * BASE_DELAY_MS)


def _parse_body(resp: Any, retry_after: Optional[int]) -> Any:
    try:
        return resp.json()
    except ValueError as exc:
        status = int(getattr(resp, "status_code", 0) or 0)
        message = f"API request failed (HTTP {status})" if status >= 400 else "Failed to parse API response"
        raise ApiError(
            message, http=status, body=str(getattr(resp, "text", "") or "")[:500], retry_after_ms=retry_after
        ) from exc


def request_json(
    method: str,
    url: str,
    *,
    json: Any = None,
    params: Optional[Mapping[str, Any]] = None,
    timeout: int = 120,
    policy: Optional[str] = None,
    max_attempts: int = DEFAULT_RETRIES + 1,
    expect_data: bool = True,
) -> Any:
    """发请求、解信封，按端点策略重试；失败抛 ApiError，failList 非空抛 PartialResultError。"""
    spec = _endpoint_policy(str(url))
    resolved = policy or str(spec.get("retry") or "retry")
    attempt = 0
    while True:
        try:
            resp = authorized_request(method, url, json=json, params=params, timeout=timeout)
            retry_after = _parse_retry_after_ms(resp.headers.get("Retry-After"))
            body = _parse_body(resp, retry_after)
            try:
                data = unwrap(body, http=resp.status_code, expect_data=expect_data)
            except ApiError as err:
                if err.retry_after_ms is None:
                    err.retry_after_ms = retry_after
                if resp.status_code == 429 and not err.code:
                    err.code = "999006"
                    err.hint = err.hint or hint_for(err.code, err.message)
                raise
            if spec.get("item_failures"):
                fail = _fail_list_of(data)
                if fail:
                    raise PartialResultError(
                        f"部分失败 failList={fail}",
                        code=str((body or {}).get("code") or "000000"),
                        trace_id=str((body or {}).get("traceId") or ""),
                    )
            return data
        except PartialResultError:
            raise
        except (ApiError, requests.RequestException) as err:
            if attempt + 1 >= max_attempts or not _is_retryable(err, resolved):
                raise
            delay = _backoff_ms(attempt, err)
            if os.getenv("GANGTISE_VERBOSE", "").lower() in {"1", "true", "yes"}:
                print(f"[gangtise] retry {attempt + 1}/{max_attempts - 1} in {int(delay)}ms: {err}", file=sys.stderr)
            time.sleep(delay / 1000.0)
            attempt += 1


# ── 按行计费列表的积分防护 ──
# 与 core/src/gangtise_core/billing.py 一致，ROW_BILLING_PRICES / COSTLY_FETCH_CREDITS 由 scripts/check_skills.py 比对。

COSTLY_FETCH_CREDITS = 1000

CREDIT_GUARD_ENV = "GANGTISE_CREDIT_GUARD"


def credit_guard_enabled() -> bool:
    """积分防护开关：默认开启；环境变量 GANGTISE_CREDIT_GUARD 为 0/false/no/off 时关闭。"""
    return (os.getenv(CREDIT_GUARD_ENV) or "").strip().lower() not in {"0", "false", "no", "off"}


# 平台公开价目（积分/条）；客户端无法测量实际扣费，缺省不代表免费。
ROW_BILLING_PRICES: Dict[str, float] = {
    "/chief-opinion/v2/getList": 1,
    "/chief-opinion/getList": 30,
    "/foreign-opinion/v2/getList": 1,
    "/foreign-opinion/getList": 30,
    "/independent-opinion/getList": 5,
    "/schedule/roadshow/getList": 20,
    "/schedule/site-visit/getList": 20,
    "/schedule/strategy-meeting/getList": 20,
    "/schedule/forum/getList": 20,
    "/schedule/performance-calendar/getList": 0.1,
    "/summary/highlight/getList": 5,
    "/security-clue/getList": 5,
    "/hot-topic/getList": 50,
    "/stock-summary/getList": 3,
}


def row_billing_price(url: str) -> Optional[float]:
    u = str(url or "").split("?", 1)[0].rstrip("/")
    best: Optional[float] = None
    best_len = -1
    for path, price in ROW_BILLING_PRICES.items():
        if u.endswith(path) and len(path) > best_len:
            best, best_len = float(price), len(path)
    return best


def guard_row_billed_fetch(
    url: str,
    payload: Mapping[str, Any],
    limit: Optional[int],
    *,
    confirm: bool = False,
    start: int = 0,
    timeout: int = 120,
) -> None:
    """limit × 单价 ≤ 防护线直接放行；否则用 size=1 探测 total，估算超线且未确认时抛 ValidationError。"""
    price = row_billing_price(url)
    if price is None or confirm or limit is None or limit <= 0 or not credit_guard_enabled():
        return
    if limit * price <= COSTLY_FETCH_CREDITS:
        return
    total: Optional[int] = None
    try:
        data = request_json("POST", url, json={**dict(payload), "from": start, "size": 1}, timeout=timeout)
        raw = data.get("total") if isinstance(data, dict) else None
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            total = int(raw)
    except ValidationError:
        raise
    except Exception:
        total = None
    rows = limit if total is None else min(max(total - start, 0), limit)
    credits = round(rows * price, 2)
    if credits <= COSTLY_FETCH_CREDITS:
        return
    seen = f"共 {total} 条" if total is not None else "总数未知（按 limit 估算）"
    raise ValidationError(
        f"按当前条件将拉取 {rows} 条（limit={limit}，{seen}），该接口按条计费，预计积分消耗较大，已拒绝；"
        "为获取总数已取 1 条。"
        "请缩小时间范围/筛选条件或调小 limit；确需全部拉取须先征得用户同意，再加 --yes（MCP 传 confirm=true）。"
    )
