"""Actionable hints for Gangtise error codes, ported from gangtise-openapi-cli `src/core/errors.ts`.

A hint is appended after the server's own msg, so it carries the *action* and never
restates the diagnosis. Both code generations are kept: the 2026-07-17 overhaul emits
new codes (as JSON numbers) while the outer token filter still emits legacy ones.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Pattern

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


def distinct_failure_shapes(message: str) -> int:
    """How many distinct failure shapes one EDE batch message describes (unparsed → 1)."""
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
    return distinct_failure_shapes(message) <= 1


def _batch(message: str) -> bool:
    return distinct_failure_shapes(message) > 1


_EDE = ("100001", "100003")

# Order matters only between the swap rule (③) and the lone 缺 tradeDate rule (⑤):
# shape ③ matches both, and ③ must come first.
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
    """Message-specific hint beats the per-code one; unknown / empty code → None."""
    code = str(code or "")
    if not code:
        return None
    for rule in MESSAGE_HINTS:
        if rule.applies(code, message or ""):
            return rule.hint
    return ERROR_HINTS.get(code)
