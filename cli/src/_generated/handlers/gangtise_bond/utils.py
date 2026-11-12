# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-bond/scripts/utils.py
# Regenerate: python3 scripts/generate.py
if __name__ == "__main__" and not __package__:
    import importlib.util
    from pathlib import Path as _P
    _launch = _P(__file__).resolve().parent / "_launch.py"
    _spec = importlib.util.spec_from_file_location("_gts_skill_launch", _launch)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(_mod)
    raise SystemExit(_mod.relaunch(__file__))

import datetime
import json
import os
import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import pandas as pd
import requests


from gangtise_core.auth import (
    append_consumed_points_to_saved_file,
    apply_consumed_points,
    authorized_request,
    get_authorization_headers,
    get_authorization_token,
    get_headers_extra,
    gangtise_domain,
)
from gangtise_core.skill_runtime import ApiError, failure_result, request_json, success_result


def __getattr__(name):
    if name == "GTS_AUTHORIZATION":
        return get_authorization_token()
    if name == "HEADERS_EXTRA":
        return get_headers_extra()
    raise AttributeError(name)


DEPLOY_ENV = os.getenv("DEPLOY_ENV", "local")


def _env_truthy(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


GTS_SAVE_FILE = _env_truthy("GTS_SAVE_FILE", False)
GTS_SAVE_EXTENSION = os.getenv("GTS_SAVE_EXTENSION", "md")

GANGTISE_QUOTE_DOMAIN = gangtise_domain("GANGTISE_QUOTE_DOMAIN", "https://openapi.gangtise.com/application/open-quote")
GANGTISE_FUNDAMENTAL_DOMAIN = gangtise_domain("GANGTISE_FUNDAMENTAL_DOMAIN", "https://openapi.gangtise.com/application/open-fundamental")
GANGTISE_REFERENCE_DOMAIN = gangtise_domain("GANGTISE_REFERENCE_DOMAIN", "https://openapi.gangtise.com/application/open-reference")
SECURITIES_SEARCH_URL = GANGTISE_REFERENCE_DOMAIN + "/securities/search"
CONSTANTS_LIST_URL = GANGTISE_REFERENCE_DOMAIN + "/constants/getList"
BOND_DAILY_QUOTE_URL = GANGTISE_QUOTE_DOMAIN + "/bond/daily-quote-exchange-cfets"
BOND_BASIC_INFO_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/bond/basic-info"
BOND_VALUATION_SHCLEARING_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/bond/valuation-shclearing"
BOND_CASH_FLOW_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/bond/cash-flow"
BOND_ANNOUNCEMENT_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/bond/announcement"
BOND_ISSUANCE_DETAIL_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/bond/issuance-detail"
BOND_RATING_OVERVIEW_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/bond/rating-overview"
BOND_ISSUANCE_PLAN_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/bond/issuance-plan"
BOND_ISSUER_INFO_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/bond/issuer-info"
BOND_ISSUER_RATING_CHANGE_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/bond/issuer-rating-change"
BOND_RATING_CHANGE_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/bond/rating-change"
BOND_EXERCISE_NOTICE_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/bond/exercise-notice"
BOND_DEFAULT_LIST_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/bond/default-list"
GANGTISE_INDICATOR_DOMAIN = gangtise_domain("GANGTISE_INDICATOR_DOMAIN", "https://openapi.gangtise.com/application/open-indicator")
INDICATOR_SEARCH_URL = GANGTISE_INDICATOR_DOMAIN + "/EDE/search"
INDICATOR_TIME_SERIES_URL = GANGTISE_INDICATOR_DOMAIN + "/EDE/time-series"
INDICATOR_CROSS_SECTION_URL = GANGTISE_INDICATOR_DOMAIN + "/EDE/cross-section"
FINANCIAL_REPORT_INCOME_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/financial-report/income-statement/accumulated"
FINANCIAL_REPORT_INCOME_QUARTERLY_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/financial-report/income-statement/quarterly"
HK_FINANCIAL_REPORT_INCOME_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/financial-report/income-statement/hk"
US_FINANCIAL_REPORT_INCOME_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/financial-report/income-statement/us"
FINANCIAL_REPORT_BALANCE_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/financial-report/balance-sheet/accumulated"
HK_FINANCIAL_REPORT_BALANCE_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/financial-report/balance-sheet/hk"
US_FINANCIAL_REPORT_BALANCE_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/financial-report/balance-sheet/us"
FINANCIAL_REPORT_CASH_FLOW_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/financial-report/cash-flow-statement/accumulated"
FINANCIAL_REPORT_CASH_FLOW_QUARTERLY_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/financial-report/cash-flow-statement/quarterly"
HK_FINANCIAL_REPORT_CASH_FLOW_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/financial-report/cash-flow-statement/hk"
US_FINANCIAL_REPORT_CASH_FLOW_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/financial-report/cash-flow-statement/us"

WORK_PATH = os.getenv("WORK_PATH", None)


def _find_openclaw_root() -> str:
    """向上遍历目录直到找到 .openclaw / .agent / workspace / skills。"""
    path = os.path.abspath(os.path.dirname(__file__))
    for marker in (".openclaw", ".agent", "workspace"):
        cur = path
        while cur != os.path.dirname(cur):
            if os.path.basename(cur) == marker:
                return os.path.abspath(cur)
            cur = os.path.dirname(cur)
    cur = path
    while cur != os.path.dirname(cur):
        if os.path.basename(cur) == "skills":
            return os.path.abspath(os.path.dirname(cur))
        cur = os.path.dirname(cur)
    return os.path.abspath(os.getcwd())


def resolve_gangtise_workspace_path() -> str:
    if WORK_PATH:
        base = WORK_PATH
    elif DEPLOY_ENV == "local":
        openclaw_root = _find_openclaw_root()
        if openclaw_root.endswith("workspace"):
            base = os.path.join(openclaw_root, "gangtise")
        else:
            base = os.path.join(openclaw_root, "workspace", "gangtise")
    else:
        base = "/opt/data/workspace/default"
    os.makedirs(base, exist_ok=True)
    os.makedirs(os.path.join(base, "files"), exist_ok=True)
    os.makedirs(os.path.join(base, ".usage"), exist_ok=True)
    return base


gangtise_workspace_path = resolve_gangtise_workspace_path()


def _unique_result_path(process_dir: str, module_name: str, extension: str) -> str:
    """日期、微秒和随机后缀独占创建，避免只靠时分秒重名。"""
    os.makedirs(process_dir, exist_ok=True)
    ext = (extension or "dat").lstrip(".") or "dat"
    stem = module_name or "result"
    for _ in range(8):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        suffix = uuid.uuid4().hex[:8]
        path = os.path.join(process_dir, f"{stem}_{stamp}_{suffix}.{ext}")
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            continue
        except OSError:
            continue
        else:
            os.close(fd)
            return path
    raise RuntimeError("结果文件无法写入，请稍后重试")


def alloc_result_path(
    method_name: str,
    module_name: str,
    extension: str,
    output_dir: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    process_dir = output_dir or os.path.join(gangtise_workspace_path, method_name)
    try:
        return _unique_result_path(process_dir, module_name, extension), None
    except RuntimeError as exc:
        return None, f"错误信息：{exc}"


def remove_html_tags(text):
    clean = re.compile("<.*?>")
    return re.sub(clean, "", text)


def _md_cell(value: Any, max_cell_length: Optional[int]) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = re.sub(r"\s+", " ", str(value).replace("\n", " ")).replace("|", "")
    if max_cell_length and len(text) > max_cell_length:
        return text[:max_cell_length] + "..."
    return text


def data_to_md(data: pd.DataFrame, range: List[int] = None, max_cell_length: int = None):
    content = "| " + " | ".join(data.columns) + " |\n"
    content += "| " + " | ".join(["-" for _ in data.columns]) + " |\n"
    omitted = False
    for i, row in enumerate(data.to_dict(orient="records")):
        if range is not None and i not in range:
            if not omitted:
                content += "| ... |\n"
                omitted = True
            continue
        content += "| " + " | ".join(_md_cell(row[key], max_cell_length) for key in row.keys()) + " |\n"
    return content.strip()


METHOD_NAME_MAP = {
    "security": "债券检索",
    "basic_info": "债券基本资料",
    "quote": "债券日收盘行情",
    "valuation": "上清所估值",
    "cash_flow": "债券付息兑付明细",
    "announcement": "债券公告",
    "issuance": "债券发行增发明细",
    "rating": "债券评级一览",
    "rating_change": "债项评级变动",
    "issuance_plan": "利率债发行计划",
    "issuer_info": "发债主体基本信息",
    "issuer_rating_change": "发债主体评级变动",
    "exercise_notice": "含权债行权提示",
    "default_list": "违约债券",
}

PREVIEW_MAX_CELL_LENGTH = 60


def format_response(response: dict, method_name: str, output_dir: Optional[str] = None):
    points_note = apply_consumed_points(response)
    if response.get("state") != "success":
        return failure_result(response)

    return_message = response.get("message", "") + "\n\n" if response.get("message", "") else ""
    for item in response.get("data") or []:
        module_name = item["module"]
        data = pd.DataFrame(item["data"])
        process_path, err = alloc_result_path(method_name, module_name, "csv", output_dir)
        if err:
            return failure_result({"message": err})
        data.to_csv(process_path, index=False)
        append_consumed_points_to_saved_file(process_path, points_note)
        # ≤100 行全量展示；超出则正文展示前 3 + 后 3 行，完整数据在 csv
        n = len(data)
        if n <= 100:
            sample_range = list(range(n))
            sample_note = f"\n\n共 {n} 行"
            data_heading = "#### 数据:\n"
        else:
            sample_range = [0, 1, 2, n - 3, n - 2, n - 1]
            sample_note = f"\n\n（展示前 3 行与后 3 行，共 {n} 行；完整数据见文件）"
            data_heading = "#### 样例数据:\n"
        sample_data = data_to_md(data, range=sample_range, max_cell_length=PREVIEW_MAX_CELL_LENGTH)
        item_footer = item.get("footer") or response.get("footer")
        footer_block = str(item_footer).strip() + "\n\n" if item_footer and str(item_footer).strip() else ""
        return_message += (
            "### "
            + METHOD_NAME_MAP.get(method_name, method_name)
            + " "
            + module_name
            + "\n\n"
            + footer_block
            + data_heading
            + sample_data
            + sample_note
            + "\n\n数据已保存到csv：\n`"
            + os.path.abspath(process_path)
            + "`\n\n---\n\n"
        )
    if return_message.endswith("---\n\n"):
        return_message = return_message[:-6].strip()
    return success_result(return_message, response)


def error_response(method_name: str, message: str, output_dir: Optional[str] = None):
    return format_response({"state": "error", "message": message, "data": []}, method_name, output_dir=output_dir)


def build_headers() -> Optional[dict]:
    if not get_authorization_token():
        return None
    return get_authorization_headers()


def parse_str_list(raw) -> List[str]:
    """将逗号分隔字符串或列表统一解析为非空字符串列表（MCP/CLI 均可传入）。"""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(s).strip() for s in raw if str(s).strip()]
    text = str(raw).strip()
    if not text:
        return []
    return [x.strip() for x in text.replace("，", ",").replace("、", ",").split(",") if x.strip()]


_SECURITY_FILE_COLUMNS = ("security_code", "code", "代码", "债券代码", "security_abbr", "债券简称")


def load_securities_from_file(path: str) -> List[str]:
    """从 CSV 读取债券列表。须为已存在的 ``.csv``；列优先 ``security_code`` / ``code`` / ``代码`` / ``债券代码`` / ``security_abbr`` / ``债券简称``。"""
    raw = os.path.expanduser((path or "").strip().strip('"').strip("'"))
    if not raw:
        raise ValueError("证券文件路径为空")
    if not raw.lower().endswith(".csv"):
        raise ValueError(f"证券文件须为 .csv：{path}")
    if not os.path.isfile(raw):
        raise FileNotFoundError(f"证券文件不存在: {path}")
    df = pd.read_csv(raw, dtype=str)
    col = next((name for name in _SECURITY_FILE_COLUMNS if name in df.columns), None)
    if col is None:
        raise ValueError(f"证券文件须包含 {' / '.join(_SECURITY_FILE_COLUMNS)} 列之一")
    return [str(x).strip() for x in df[col].dropna().tolist() if str(x).strip()]


def normalize_securities_arg(securities) -> List[str]:
    """解析 ``--securities``：代码/简称逗号分隔；以 ``.csv`` 结尾的 token 按文件读入。"""
    out: List[str] = []
    for t in parse_str_list(securities):
        items = load_securities_from_file(t) if t.lower().endswith(".csv") else [t]
        for x in items:
            x = str(x).strip()
            if x and x not in out:
                out.append(x)
    return out


def chunked(items: Sequence[Any], size: int) -> List[List[Any]]:
    return [list(items[i:i + size]) for i in range(0, len(items), size)]


def default_date_range(
    start_date: Optional[str],
    end_date: Optional[str],
    back_days: int = 7,
    forward_days: int = 0,
) -> Tuple[str, str]:
    """补齐必填的日期区间：均未传时取 [今天-back_days, 今天+forward_days]；只传一端时以另一端的默认值补齐。"""
    today = datetime.date.today()
    start = start_date or (today - datetime.timedelta(days=back_days)).strftime("%Y-%m-%d")
    end = end_date or (today + datetime.timedelta(days=forward_days)).strftime("%Y-%m-%d")
    return start, end


OPEN_RANGE_START = "1980-01-01"
OPEN_RANGE_END = "2099-12-31"


def apply_optional_date_range(payload: dict, start_date: Optional[str], end_date: Optional[str]) -> dict:
    """可选日期区间：接口要求 startDate / endDate 同传或同不传，只给一端时另一端放开到极值。"""
    if start_date or end_date:
        payload["startDate"] = start_date or OPEN_RANGE_START
        payload["endDate"] = end_date or OPEN_RANGE_END
    return payload


# 行情、估值接口按「日历天数 × 债券只数」预估行数，超过 10000 即以 100006 拒绝（与实际行数无关）
DAILY_SPAN_BUDGET = 10000


def daily_payloads(codes: Sequence[str], start: str, end: str, base_payload: dict) -> List[dict]:
    """按 天数 × 只数 ≤ DAILY_SPAN_BUDGET 拆分债券，生成同一日期区间的多组请求。"""
    days = (_parse_date(end) - _parse_date(start)).days + 1 if _parse_date(start) and _parse_date(end) else 1
    size = max(1, DAILY_SPAN_BUDGET // max(days, 1))
    return [dict(base_payload, securityList=chunk, startDate=start, endDate=end) for chunk in chunked(list(codes), size)]


# 付息兑付、发行增发接口同样按「日期跨度天数 × 债券只数」预估行数，约 25000 即拒绝；留出余量后按此预算拆分请求
SPAN_BUDGET_DAYS = 20000
_LIFETIME_MARGIN_DAYS = 31
_LIFETIME_FALLBACK = (datetime.date(1990, 1, 1), datetime.date.today() + datetime.timedelta(days=366 * 50))


def _parse_date(value) -> Optional[datetime.date]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def fetch_bond_lifetimes(
    codes: Sequence[str],
    headers: dict,
    dropped: Optional[List[str]] = None,
) -> Dict[str, Tuple[datetime.date, datetime.date]]:
    """从债券基本资料取每只债券的存续区间 [发行公告日/起息日, 到期日]，前后各留一个月余量；查不到的给宽区间。"""
    fields = ["issueAnnouncementDate", "issueDate", "valueDate", "maturityDate", "actualMaturityDate"]
    out: Dict[str, Tuple[datetime.date, datetime.date]] = {}
    dropped = dropped if dropped is not None else []
    for chunk in chunked(list(codes), 10000):
        payload = {"securityList": chunk, "fieldList": fields}
        df, _ = post_bond_table(BOND_BASIC_INFO_URL, payload, headers, dropped=dropped)
        for row in df.to_dict(orient="records") if not df.empty else []:
            starts = [d for d in (_parse_date(row.get(f)) for f in fields[:3]) if d]
            ends = [d for d in (_parse_date(row.get(f)) for f in fields[3:]) if d]
            if starts and ends:
                margin = datetime.timedelta(days=_LIFETIME_MARGIN_DAYS)
                out[row["securityCode"]] = (min(starts) - margin, max(ends) + margin)
    return out


def plan_lifetime_payloads(
    codes: Sequence[str],
    start_date: Optional[str],
    end_date: Optional[str],
    base_payload: dict,
    headers: dict,
    max_per_request: Optional[int] = None,
) -> List[dict]:
    """
    为「日期区间可选、按跨度×只数预估行数」的接口生成请求：每只债券的查询区间取其存续期与用户区间的交集，
    再把区间相近的债券打包，使每个请求的 跨度天数 × 只数 不超过 SPAN_BUDGET_DAYS；单只债券跨度超限时按时间切段。
    """
    user_lo = _parse_date(start_date)
    user_hi = _parse_date(end_date)
    invalid: List[str] = []
    lifetimes = fetch_bond_lifetimes(codes, headers, dropped=invalid)

    windows: List[Tuple[str, datetime.date, datetime.date]] = []
    for code in codes:
        if code in invalid:
            continue
        lo, hi = lifetimes.get(code, _LIFETIME_FALLBACK)
        lo = max(lo, user_lo) if user_lo else lo
        hi = min(hi, user_hi) if user_hi else hi
        if lo > hi:
            continue
        span = (hi - lo).days + 1
        if span <= SPAN_BUDGET_DAYS:
            windows.append((code, lo, hi))
            continue
        cursor = lo
        while cursor <= hi:
            seg_hi = min(hi, cursor + datetime.timedelta(days=SPAN_BUDGET_DAYS - 1))
            windows.append((code, cursor, seg_hi))
            cursor = seg_hi + datetime.timedelta(days=1)

    windows.sort(key=lambda w: (w[1], w[2]))
    payloads: List[dict] = []
    group: List[str] = []
    g_lo = g_hi = None

    def flush():
        if group:
            payloads.append(dict(base_payload, securityList=list(group),
                                 startDate=g_lo.strftime("%Y-%m-%d"), endDate=g_hi.strftime("%Y-%m-%d")))

    for code, lo, hi in windows:
        if group:
            n_lo, n_hi = min(g_lo, lo), max(g_hi, hi)
            fits = ((n_hi - n_lo).days + 1) * (len(group) + 1) <= SPAN_BUDGET_DAYS
            fits = fits and code not in group and (not max_per_request or len(group) < max_per_request)
            if fits:
                group.append(code)
                g_lo, g_hi = n_lo, n_hi
                continue
            flush()
        group, g_lo, g_hi = [code], lo, hi
    flush()
    return payloads


def sort_by_codes(df: pd.DataFrame, codes: Sequence[str], date_col: str) -> pd.DataFrame:
    """分批请求的结果按用户传入的债券顺序、再按日期升序排列。"""
    if df.empty or "securityCode" not in df.columns:
        return df
    order = {c: i for i, c in enumerate(codes)}
    keys = ["_order"] + ([date_col] if date_col in df.columns else [])
    out = df.assign(_order=df["securityCode"].map(order).fillna(len(order)))
    return out.sort_values(keys, kind="stable").drop(columns="_order").reset_index(drop=True)


def describe_period(start_date: Optional[str], end_date: Optional[str]) -> str:
    if not start_date and not end_date:
        return ""
    return f" {start_date or '最早'}~{end_date or '最晚'}"


def _strip_unit_suffix(label: str) -> str:
    return re.sub(r"[（(][^（）()]*[)）]$", "", label).strip()


def resolve_field_list(
    raw,
    field_cn: Dict[str, str],
    default_keys: Sequence[str],
    default_fields: Optional[Sequence[str]] = None,
) -> Tuple[Optional[List[str]], Optional[str]]:
    """
    将 ``--field-list``（英文字段名或中文名，逗号分隔）解析为接口 fieldList。
    不传返回 default_fields（None 表示全部字段）；传 ``all`` 返回 []（接口语义为全部字段）。
    """
    tokens = parse_str_list(raw)
    if not tokens:
        return (list(default_fields) if default_fields else []), None
    if len(tokens) == 1 and tokens[0].lower() == "all":
        return [], None

    lookup: Dict[str, str] = {}
    for en, cn in field_cn.items():
        for key in (en.lower(), cn, _strip_unit_suffix(cn)):
            lookup.setdefault(key, en)

    out: List[str] = []
    bad: List[str] = []
    for t in tokens:
        en = t if t in field_cn else (lookup.get(t) or lookup.get(t.lower()))
        if not en:
            bad.append(t)
        elif en not in out:
            out.append(en)
    if bad:
        selectable = ", ".join(f"{k}({v})" for k, v in field_cn.items() if k not in default_keys)
        return None, f"不支持的字段：{bad}。可选字段：{selectable}"
    return out or list(default_keys), None


_ERROR_HINTS = {
    "100006": "结果超出单次 10000 行上限，请缩短日期区间或减少债券数量后重试",
    "110001": "日期格式不受支持，请使用 yyyy-MM-dd",
    "110002": "开始日期不能晚于结束日期",
    "110003": "超出账号可查询的历史区间（试用账号前溯 3 年、正式账号前溯 5 年），请把开始日期调晚后重试",
    "120001": "债券代码格式无效（须为 .SH/.SZ/.BJ/.IB 后缀的标准代码），可直接传债券简称由脚本自动解析",
}

_INVALID_CODES_PATTERN = re.compile(r"\[([^\[\]]*)\]")


def post_bond_table(
    url: str,
    payload: dict,
    headers: dict,
    timeout: int = 120,
    retries: int = 2,
    dropped: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    请求「表头 fieldList + 位置数组 list」结构的债券接口。
    返回 (DataFrame, 错误信息)；130001（全部查询键无数据）视为空结果而非错误。
    120001 会点名非法代码并整批拒绝（如公告接口返回的未发行债券占位代码），此时剔除这些代码后重试，
    被剔除的代码追加到 dropped。
    """
    df, err, invalid = _post_bond_table_once(url, payload, headers, timeout, retries)
    codes = payload.get("securityList")
    if invalid and codes:
        remaining = [c for c in codes if c not in invalid]
        if len(remaining) < len(codes):
            if dropped is not None:
                dropped.extend(c for c in codes if c in invalid and c not in dropped)
            if not remaining:
                return pd.DataFrame(), None
            return post_bond_table(url, dict(payload, securityList=remaining), headers, timeout, retries, dropped)
    return df, err


def _post_bond_table_once(
    url: str,
    payload: dict,
    headers: dict,
    timeout: int,
    retries: int,
) -> Tuple[pd.DataFrame, Optional[str], List[str]]:
    # 债券接口按次计费，重放 5xx / 超时 / 999999 会重复扣费：
    # 只按 endpoints.yaml 的 no-replay 策略在 429 与连接阶段失败时重试。
    try:
        block = request_json("POST", url, json=payload, timeout=timeout, policy="no-replay", max_attempts=retries + 1)
    except ApiError as e:
        code = e.code
        if code == "130001":
            return pd.DataFrame(), None, []
        body = e.body if isinstance(e.body, dict) else {}
        error_type = body.get("errorType")
        msg = e.message
        if not code:
            return pd.DataFrame(), f"HTTP {e.http}: {msg}", []
        tag = f"{code}/{error_type}" if error_type else code
        hint = _ERROR_HINTS.get(code)
        invalid: List[str] = []
        if code == "120001":
            for group in _INVALID_CODES_PATTERN.findall(str(msg)):
                invalid.extend(x.strip().upper() for x in group.split(",") if x.strip())
        return pd.DataFrame(), f"[{tag}] {msg}" + (f"（{hint}）" if hint else ""), invalid
    except requests.RequestException as e:
        return pd.DataFrame(), f"请求失败: {e}", []

    block = block if isinstance(block, dict) else {}
    fields = block.get("fieldList") or []
    rows = block.get("list") or []
    if not fields or not rows:
        return pd.DataFrame(columns=fields), None, []
    bad_rows = [row for row in rows if not isinstance(row, (list, tuple)) or len(row) != len(fields)]
    if bad_rows:
        return pd.DataFrame(), f"接口返回的数据行与表头长度不一致（表头 {len(fields)} 列），已拒绝解析以避免错位", []
    return pd.DataFrame([list(row) for row in rows], columns=fields), None, []


# 枚举字段 → 常量分类（见 open-reference/constants/category 的 usageScopes）；
# issuerRegion 的省市代码实际落在 domesticCity，regionCategory 只含国家/地区级代码
CONSTANT_FIELD_CATEGORIES = {
    "bondType": ("bondType",),
    "interestRateType": ("interestRateType",),
    "interestFrequency": ("interestFrequency",),
    "absUnderlyingAssetType": ("absUnderlyingAssetType",),
    "issuerRegion": ("regionCategory", "domesticCity"),
    "industry": ("nationalEconomicIndustry",),
    "exchange": ("exchange",),
    "ratingType": ("ratingType",),
}
_CONSTANT_CODE_PATTERN = re.compile(r"^\d{6,}$")
_constants_cache: Dict[str, Dict[str, str]] = {}


def _load_constants(category: str, headers: dict) -> Dict[str, str]:
    if category in _constants_cache:
        return _constants_cache[category]
    mapping: Dict[str, str] = {}
    try:
        r = authorized_request("POST", CONSTANTS_LIST_URL, headers=headers, json={"category": category}, timeout=30)
        body = r.json()
        if str(body.get("code", "")) == "000000":
            for item in (body.get("data") or {}).get("constants") or []:
                if item.get("constantId") is not None:
                    mapping[str(item["constantId"])] = item.get("constantName")
    except Exception:
        pass
    _constants_cache[category] = mapping
    return mapping


def decode_constants(df: pd.DataFrame, headers: dict) -> pd.DataFrame:
    """将枚举字段的常量代码替换为常量名称；常量表中查不到的代码保留原值。"""
    out = df.copy()
    for col in out.columns:
        categories = CONSTANT_FIELD_CATEGORIES.get(col)
        if not categories:
            continue
        if not any(_CONSTANT_CODE_PATTERN.match(str(v)) for v in out[col].dropna()):
            continue
        mapping: Dict[str, str] = {}
        for category in categories:
            mapping.update(_load_constants(category, headers))
        if mapping:
            out[col] = out[col].map(lambda v: mapping.get(str(v), v) if v is not None and not pd.isna(v) else v)
    return out


def _trim_float(v: Any) -> Any:
    """去掉二进制浮点误差尾数（如 -6.5600000000000005 → -6.56）；15 位有效数字以内无损。"""
    if isinstance(v, float) and not pd.isna(v):
        return float(f"{v:.15g}")
    return v


def to_display_df(df: pd.DataFrame, field_cn: Dict[str, str]) -> pd.DataFrame:
    """布尔列转 是/否，浮点去误差尾数，列名转中文。"""
    out = df.copy()
    for col in out.columns:
        values = out[col].dropna()
        if len(values) and all(isinstance(v, bool) for v in values):
            out[col] = out[col].map(lambda v: None if v is None or pd.isna(v) else ("是" if v else "否"))
        elif out[col].dtype.kind == "f" or any(isinstance(v, float) for v in values):
            out[col] = out[col].map(_trim_float)
    return out.rename(columns={k: v for k, v in field_cn.items() if k in out.columns})


def describe_securities(codes: Sequence[str], abbrs: Sequence[str]) -> str:
    if not codes:
        return ""
    first = f"{abbrs[0]}({codes[0]})" if abbrs and abbrs[0] else codes[0]
    return first if len(codes) == 1 else f"{first}等{len(codes)}只债券"


def run_table_query(
    *,
    url: str,
    method_name: str,
    module_name: str,
    title: str,
    payloads: List[dict],
    field_cn: Dict[str, str],
    headers: dict,
    output_dir: Optional[str] = None,
    notes: Optional[List[str]] = None,
    post_process: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None,
    timeout: int = 120,
    fallback: Optional[Tuple[List[dict], str, str]] = None,
) -> str:
    """
    按 payloads 依次请求并拼接结果，转中文列名后落盘为 CSV。
    fallback=(payloads, title, note)：首轮全部无数据时改用这组请求再查一次（如默认区间遇长假时放宽区间）。
    """
    dropped: List[str] = []

    def fetch(batch: List[dict]) -> Tuple[List[pd.DataFrame], Optional[str]]:
        frames: List[pd.DataFrame] = []
        for payload in batch:
            df, err = post_bond_table(url, payload, headers, timeout=timeout, dropped=dropped)
            if err:
                return [], err
            if not df.empty:
                frames.append(df)
        return frames, None

    notes = list(notes or [])
    frames, err = fetch(payloads)
    if dropped:
        listed = "、".join(dropped[:10]) + (f" 等 {len(dropped)} 只" if len(dropped) > 10 else "")
        notes.append(f"[WARNING]以下代码不被该接口接受（如尚未发行的占位代码），已跳过：{listed}")
    if err:
        return error_response(method_name, f"{title}查询失败：{err}", output_dir)
    if not frames and fallback:
        fb_payloads, fb_title, fb_note = fallback
        frames, err = fetch(fb_payloads)
        if err:
            return error_response(method_name, f"{fb_title}查询失败：{err}", output_dir)
        if frames:
            title = fb_title
            notes.insert(0, fb_note)
    if not frames:
        return error_response(method_name, f"未找到{title}", output_dir)

    data = pd.concat(frames, ignore_index=True)
    if post_process:
        data = post_process(data)
        if data.empty:
            return error_response(method_name, f"未找到{title}", output_dir)
    data = to_display_df(decode_constants(data, headers), field_cn)

    message = f"已找到{title}"
    for note in notes:
        if note:
            message += f"\n{note}"
    return format_response(
        {
            "state": "success",
            "message": message,
            "data": [{"data": data.to_dict(orient="records"), "module": module_name, "type": "data"}],
        },
        method_name,
        output_dir=output_dir,
    )


def add_common_args(parser, field_help: str) -> None:
    parser.add_argument("--field-list", default=None, help=field_help)
    parser.add_argument("-od", "--output-dir", default=None, help="结果保存目录路径，建议使用绝对路径")


OPENAPI_SKILL_VERSION = "1.7.0"
SKILL_CHECK_URL = "https://openapi.gangtise.com/application/skills-backend/version?skill=openapi"


def check_version(large_version: bool = True) -> bool:
    response = requests.get(SKILL_CHECK_URL, timeout=15)
    if response.status_code != 200:
        return False
    body = response.json()
    if body.get("state") != "success":
        return False
    remote = str(body.get("version") or "")
    local_parts = OPENAPI_SKILL_VERSION.split(".")
    remote_parts = remote.split(".")
    if large_version:
        return (
            len(remote_parts) >= 2
            and remote_parts[0] == local_parts[0]
            and remote_parts[1] == local_parts[1]
        )
    return remote == OPENAPI_SKILL_VERSION


def warn_if_outdated() -> None:
    try:
        if not check_version():
            update_sh = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update.sh")
            print(f"[WARNING] 存在 Gangtise bond 版本更新，可以执行 {update_sh} 更新，请与用户确认是否更新\n")
    except Exception:
        print("[WARNING] 检查 Gangtise bond 版本失败\n")


if __name__ == "__main__":
    print("检查 gangtise-bond 相关配置")
    if not get_authorization_token():
        print("  无法检测到gangtise密钥环境变量或授权文件, gangtise-bond 无法正常工作")
    else:
        print("  检测到gangtise授权文件, gangtise-bond 可以正常工作")
    try:
        if check_version(large_version=False):
            print("  gangtise-bond 版本为最新")
        else:
            print("  gangtise-bond 版本不是最新, 建议进行更新")
    except Exception:
        print("  检查 gangtise-bond 版本失败")
    print(f"  gangtise-bond 工作文件目录: {gangtise_workspace_path}")
