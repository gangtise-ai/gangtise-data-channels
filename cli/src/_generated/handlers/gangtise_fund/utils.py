# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-fund/scripts/utils.py
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
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd
import requests


from gangtise_core.auth import (
    authorized_request,
    get_authorization_headers,
    get_authorization_token,
    get_headers_extra,
    gangtise_domain,
)
from gangtise_core.skill_runtime import failure_result, success_result


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

FUND_BASIC_INFO_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/basic-info"
FUND_FEE_RATE_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/fee-rate"
FUND_MANAGER_HISTORY_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/manager-history"
FUND_ASSET_ALLOCATION_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/asset-allocation"
FUND_INDUSTRY_ALLOCATION_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/industry-allocation"
FUND_BOND_TYPE_ALLOCATION_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/bond-type-allocation"
FUND_FUND_TYPE_ALLOCATION_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/fund-type-allocation"
FUND_STOCK_PORTFOLIO_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/stock-portfolio"
FUND_BOND_PORTFOLIO_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/bond-portfolio"
FUND_FUND_PORTFOLIO_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/fund-portfolio"
FUND_ASSET_SIZE_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/asset-size"
FUND_HOLDER_STRUCTURE_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/holder-structure"
FUND_TOP10_HOLDERS_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/top10-holders"
FUND_NAV_URL = GANGTISE_QUOTE_DOMAIN + "/fund/nav"
FUND_MANAGER_INFO_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/manager-info"
FUND_ETF_PCF_HEADER_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/etf-pcf-header"
FUND_ETF_PCF_COMPONENTS_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/etf-pcf-components"
FUND_ETF_SHARE_CHANGE_URL = GANGTISE_FUNDAMENTAL_DOMAIN + "/fund/etf-share-change"
GANGTISE_INDICATOR_DOMAIN = gangtise_domain("GANGTISE_INDICATOR_DOMAIN", "https://openapi.gangtise.com/application/open-indicator")
INDICATOR_SEARCH_URL = GANGTISE_INDICATOR_DOMAIN + "/EDE/search"
INDICATOR_TIME_SERIES_URL = GANGTISE_INDICATOR_DOMAIN + "/EDE/time-series"
INDICATOR_CROSS_SECTION_URL = GANGTISE_INDICATOR_DOMAIN + "/EDE/cross-section"

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


def alloc_result_path(
    method_name: str,
    module_name: str,
    extension: str,
    output_dir: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    process_dir = output_dir or os.path.join(gangtise_workspace_path, method_name)
    os.makedirs(process_dir, exist_ok=True)
    now = datetime.datetime.now().strftime("%H%M%S")
    process_path = os.path.join(process_dir, f"{module_name}_{now}.{extension}")
    max_retries = 10
    while os.path.exists(process_path) and max_retries > 0:
        time.sleep(1)
        now = datetime.datetime.now().strftime("%H%M%S")
        process_path = os.path.join(process_dir, f"{module_name}_{now}.{extension}")
        max_retries -= 1
    if max_retries == 0:
        return None, "错误信息：文件存储系统繁忙，请稍后再试"
    return process_path, None


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
    "security": "基金检索",
    "profile": "基金档案",
    "allocation": "基金持仓分布",
    "portfolio": "基金持仓明细",
    "asset_size": "基金资产规模",
    "holder_structure": "基金持有人结构",
    "top_holders": "基金前十大持有人",
    "nav": "基金净值表现",
    "manager": "基金经理信息",
    "etf_header": "ETF申赎基本资料",
    "etf_components": "ETF申赎成分股",
    "etf_share": "ETF基金份额变动",
}

PREVIEW_MAX_CELL_LENGTH = 60


def format_response(response: dict, method_name: str, output_dir: Optional[str] = None):
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


_SECURITY_FILE_COLUMNS = (
    "security_code",
    "code",
    "代码",
    "基金代码",
    "fund_code",
    "fundCode",
    "security_abbr",
    "基金简称",
)


def load_securities_from_file(path: str) -> List[str]:
    """从 CSV 读取基金列表。须为已存在的 ``.csv``。"""
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


def describe_period(start_date: Optional[str], end_date: Optional[str]) -> str:
    if not start_date and not end_date:
        return ""
    return f" {start_date or '最早'}~{end_date or '最晚'}"


def check_date_range(start_date: Optional[str], end_date: Optional[str]) -> Optional[str]:
    for name, value in (("开始日期", start_date), ("结束日期", end_date)):
        if not value:
            continue
        try:
            datetime.date.fromisoformat(str(value))
        except ValueError:
            return f"{name}须为 yyyy-MM-dd，收到：{value}"
    if start_date and end_date and start_date > end_date:
        return "开始日期不能晚于结束日期"
    return None


def _strip_unit_suffix(label: str) -> str:
    return re.sub(r"[（(][^（）()]*[)）]$", "", label).strip()


def resolve_field_list(
    raw,
    field_cn: Dict[str, str],
    default_keys: Sequence[str],
    default_fields: Optional[Sequence[str]] = None,
) -> Tuple[Optional[List[str]], Optional[str]]:
    """
    将 ``--field-list``（英文字段名或中文名，逗号分隔）解析为字段名。
    不传返回 default_fields（空列表表示全部字段）；传 ``all`` 返回 []。
    """
    tokens = parse_str_list(raw)
    if not tokens:
        return (list(default_fields) if default_fields else []), None
    if len(tokens) == 1 and tokens[0].lower() in ("all", "全部"):
        return [], None

    lookup: Dict[str, str] = {}
    for en, cn in field_cn.items():
        for key in (en, en.lower(), cn, _strip_unit_suffix(cn)):
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


def parse_types(
    raw,
    alias_to_key: Dict[str, str],
    order: Sequence[str],
    default: Sequence[str],
) -> Tuple[List[str], Optional[str]]:
    """解析 ``--type``。空值用 default；含 all/全部 时返回 order 中的全部类型。"""
    tokens = parse_str_list(raw)
    if not tokens:
        return list(default), None
    if any(t.lower() == "all" or t == "全部" for t in tokens):
        return list(order), None
    out: List[str] = []
    bad: List[str] = []
    for token in tokens:
        key = alias_to_key.get(token) or alias_to_key.get(token.lower())
        if not key:
            bad.append(token)
        elif key not in out:
            out.append(key)
    if bad:
        return [], f"不支持的 --type：{bad}。可选 {', '.join(order)}，或 all"
    return out, None


def parse_choices(raw, alias_to_value: Dict[str, str], label: str) -> Tuple[List[str], Optional[str]]:
    tokens = parse_str_list(raw)
    if not tokens:
        return [], None
    out: List[str] = []
    bad: List[str] = []
    for token in tokens:
        value = alias_to_value.get(token) or alias_to_value.get(token.lower())
        if not value:
            bad.append(token)
        elif value not in out:
            out.append(value)
    if bad:
        options: List[str] = []
        for value in alias_to_value.values():
            if value not in options:
                options.append(value)
        return [], f"不支持的{label}：{bad}。可选 {', '.join(options)}"
    return out, None


def parse_choice(raw, alias_to_value: Dict[str, str], label: str) -> Tuple[Optional[str], Optional[str]]:
    values, err = parse_choices(raw, alias_to_value, label)
    if err:
        return None, err
    if len(values) > 1:
        return None, f"{label}只能指定一个"
    return (values[0] if values else None), None


_ERROR_HINTS = {
    "100006": "结果超出单次 10000 行上限，请缩短日期区间或减少基金数量后重试",
    "110001": "日期格式不受支持，请使用 yyyy-MM-dd",
    "110002": "开始日期不能晚于结束日期",
    "120001": "基金代码格式无效，可直接传基金简称由脚本自动解析",
}


def _frame_from_block(block: dict) -> pd.DataFrame:
    """兼容对象列表，以及表头 fieldList + 位置数组 list 两种返回。"""
    rows = block.get("list") or []
    fields = block.get("fieldList") or []
    if not rows:
        return pd.DataFrame(columns=list(fields) if fields else None)
    first = rows[0]
    if isinstance(first, dict):
        return pd.DataFrame(rows)
    if fields and isinstance(first, (list, tuple)):
        bad = [row for row in rows if not isinstance(row, (list, tuple)) or len(row) != len(fields)]
        if bad:
            raise ValueError(f"接口返回的数据行与表头长度不一致（表头 {len(fields)} 列）")
        return pd.DataFrame([list(row) for row in rows], columns=list(fields))
    raise ValueError("无法识别的返回结构")


def post_fund_table(
    url: str,
    payload: dict,
    headers: dict,
    timeout: int = 120,
) -> Tuple[pd.DataFrame, Optional[str]]:
    """请求基金接口。130001（查询键无数据）视为空结果。"""
    try:
        r = authorized_request("POST", url, headers=headers, json=payload, timeout=timeout)
    except Exception as e:
        return pd.DataFrame(), f"请求失败: {e}"
    try:
        body = r.json()
    except Exception:
        return pd.DataFrame(), f"HTTP {r.status_code}: {r.text[:300]}"

    code = str(body.get("code", ""))
    if code != "000000" or body.get("status") is False:
        if code == "130001":
            return pd.DataFrame(), None
        error_type = body.get("errorType")
        msg = body.get("msg") or body.get("message") or r.text[:300]
        tag = f"{code}/{error_type}" if error_type else code
        hint = _ERROR_HINTS.get(code)
        return pd.DataFrame(), f"[{tag}] {msg}" + (f"（{hint}）" if hint else "")

    try:
        return _frame_from_block(body.get("data") or {}), None
    except ValueError as e:
        return pd.DataFrame(), str(e)


ENUM_LABELS = {
    "feeType": {
        "purchaseFee": "申购费",
        "redemptionFee": "赎回费",
        "managementFee": "管理费",
        "custodianFee": "托管费",
        "saleFee": "销售服务费",
    },
    "assetLevel": {"level1": "一级", "level2": "二级"},
    "industryStandard": {
        "swIndustry": "申万一级行业",
        "citicIndustry": "中信一级行业",
    },
    "positionType": {"top": "重仓", "all": "全部"},
}


def localize_enums(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col, mapping in ENUM_LABELS.items():
        if col not in out.columns:
            continue
        out[col] = out[col].map(lambda v, m=mapping: m.get(v, v) if isinstance(v, str) else v)
    return out


_THOUSANDS_NUMBER = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")
_PLAIN_NUMBER = re.compile(r"^-?(0|[1-9]\d*)(\.\d+)?$")


def _trim_float(v: Any) -> Any:
    """去掉二进制浮点误差尾数（如 -6.5600000000000005 → -6.56）；15 位有效数字以内无损。"""
    if isinstance(v, float) and not pd.isna(v):
        return float(f"{v:.15g}")
    return v


def _parse_thousands(v: Any) -> Any:
    if not isinstance(v, str):
        return v
    text = v.replace(",", "")
    return float(text) if "." in text else int(text)


def normalize_numbers(df: pd.DataFrame) -> pd.DataFrame:
    """接口偶有千分位字符串数字（如 holderCount="2,219,140"）与浮点尾数，统一为普通数值。"""
    out = df.copy()
    for col in out.columns:
        values = out[col].dropna()
        if not len(values):
            continue
        if all(isinstance(v, str) for v in values):
            if any(_THOUSANDS_NUMBER.match(v) for v in values) and all(
                _THOUSANDS_NUMBER.match(v) or _PLAIN_NUMBER.match(v) for v in values
            ):
                out[col] = pd.Series([_parse_thousands(v) for v in out[col]], index=out.index, dtype=object)
            continue
        if out[col].dtype.kind == "f" or any(isinstance(v, float) for v in values):
            out[col] = out[col].map(_trim_float)
    return out


def to_display_df(df: pd.DataFrame, field_cn: Dict[str, str]) -> pd.DataFrame:
    """布尔列转 是/否，枚举转中文，数值格式统一，列按字段表排序后改中文名。"""
    out = normalize_numbers(localize_enums(df))
    for col in list(out.columns):
        values = out[col].dropna()
        if len(values) and all(isinstance(v, bool) for v in values):
            out[col] = out[col].map(lambda v: None if v is None or (isinstance(v, float) and pd.isna(v)) else ("是" if v else "否"))
    ordered = [c for c in field_cn if c in out.columns]
    rest = [c for c in out.columns if c not in field_cn]
    out = out[ordered + rest]
    return out.rename(columns={k: v for k, v in field_cn.items() if k in out.columns})


def describe_securities(codes: Sequence[str], abbrs: Sequence[str]) -> str:
    if not codes:
        return ""
    first = f"{abbrs[0]}({codes[0]})" if abbrs and abbrs[0] else codes[0]
    return first if len(codes) == 1 else f"{first}等{len(codes)}只基金"


def _apply_keep(df: pd.DataFrame, keep: Optional[Sequence[str]]) -> pd.DataFrame:
    if not keep:
        return df
    cols = [c for c in keep if c in df.columns]
    for must in ("fundCode", "fundName"):
        if must in df.columns and must not in cols:
            cols.insert(0, must)
    return df[cols] if cols else df


def execute_jobs(
    *,
    method_name: str,
    headers: dict,
    jobs: List[dict],
    headline: str,
    output_dir: Optional[str] = None,
    notes: Optional[List[str]] = None,
    fallback: Optional[Tuple[List[dict], str, str]] = None,
) -> str:
    """
    依次请求 jobs，各自落盘。部分失败时成功的表仍返回，失败写在说明里。
    fallback=(jobs, headline, note)：首轮全部无数据且无报错时改用这组请求再查一次（如默认区间遇长假时放宽区间）。
    """

    def fetch(batch: List[dict]) -> Tuple[List[dict], List[str], List[str], bool]:
        found: List[str] = []
        miss: List[str] = []
        got: List[dict] = []
        failed = False
        for job in batch:
            label = job["label"]
            df, err = post_fund_table(job["url"], job["payload"], headers, timeout=job.get("timeout", 120))
            if err:
                miss.append(f"{label}查询失败：{err}")
                failed = True
                continue
            if df.empty:
                miss.append(f"未找到{label}")
                continue
            df = _apply_keep(df, job.get("keep"))
            df = to_display_df(df, job["field_cn"])
            if df.empty:
                miss.append(f"未找到{label}")
                continue
            got.append({"data": df.to_dict(orient="records"), "module": job["module"], "type": "data"})
            found.append(label)
        return got, found, miss, failed

    notes = list(notes or [])
    items, found_labels, missing, failed = fetch(jobs)
    if not items and not failed and fallback:
        fb_jobs, fb_headline, fb_note = fallback
        fb_items, fb_found, fb_missing, _ = fetch(fb_jobs)
        if fb_items:
            items, found_labels, missing, headline = fb_items, fb_found, fb_missing, fb_headline
            notes.insert(0, fb_note)

    if not items:
        detail = "；".join(missing) if missing else f"未找到{headline}"
        return error_response(method_name, detail, output_dir)

    message = f"已找到{headline}的{'、'.join(found_labels)}"
    for note in notes + missing:
        if note:
            message += f"\n{note}"
    return format_response(
        {"state": "success", "message": message, "data": items},
        method_name,
        output_dir=output_dir,
    )


def query_by_codes(
    *,
    method_name: str,
    securities: List[str],
    jobs: List[dict],
    output_dir: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    default_back_days: Optional[int] = None,
    fallback_back_days: Optional[int] = None,
    extra_notes: Optional[List[str]] = None,
) -> str:
    """
    把证券名称/代码解析为基金代码后，按 jobs 请求基金接口。
    未传日期时按 default_back_days 取默认区间；若再给 fallback_back_days，默认区间无数据（如长假）时放宽到该天数重查。
    """
    from .security import resolve_or_error

    headers = build_headers()
    if not headers:
        return error_response(method_name, "未配置 gangtise 授权，无法调用 open 接口", output_dir)
    date_err = check_date_range(start_date, end_date)
    if date_err:
        return error_response(method_name, date_err, output_dir)
    use_default = default_back_days is not None and not start_date and not end_date
    if use_default:
        start_date, end_date = default_date_range(None, None, back_days=default_back_days)

    codes, abbrs, notes, err_out = resolve_or_error(securities, headers, method_name, output_dir)
    if err_out:
        return err_out

    def build(start: Optional[str], end: Optional[str]) -> List[dict]:
        built: List[dict] = []
        for job in jobs:
            payload = {"fundCodeList": codes}
            payload.update(job.get("extra") or {})
            if start:
                payload["startDate"] = start
            if end:
                payload["endDate"] = end
            built.append({**job, "payload": payload})
        return built

    subject = describe_securities(codes, abbrs)
    fallback = None
    if use_default and fallback_back_days:
        fb_start, _ = default_date_range(None, None, back_days=fallback_back_days)
        fallback = (
            build(fb_start, end_date),
            f"{subject}{describe_period(fb_start, end_date)}",
            f"近 {default_back_days} 日无数据（可能为节假日），已放宽到近 {fallback_back_days} 日",
        )
    return execute_jobs(
        method_name=method_name,
        headers=headers,
        jobs=build(start_date, end_date),
        headline=f"{subject}{describe_period(start_date, end_date)}",
        output_dir=output_dir,
        notes=(notes or []) + (extra_notes or []),
        fallback=fallback,
    )


def add_output_arg(parser) -> None:
    parser.add_argument("-od", "--output-dir", default=None, help="结果保存目录路径，建议使用绝对路径")


def add_date_args(parser, *, daily_default: bool) -> None:
    if daily_default:
        parser.add_argument("-sd", "--start-date", default=None, help="开始日期 yyyy-MM-dd；不传默认近 7 日，无数据时放宽到近 30 日")
        parser.add_argument("-ed", "--end-date", default=None, help="结束日期 yyyy-MM-dd；不传默认今天")
    else:
        parser.add_argument("-sd", "--start-date", default=None, help="报告期开始 yyyy-MM-dd；不传则不限制")
        parser.add_argument("-ed", "--end-date", default=None, help="报告期结束 yyyy-MM-dd；不传则不限制")


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
            print(f"[WARNING] 存在 Gangtise fund 版本更新，可以执行 {update_sh} 更新，请与用户确认是否更新\n")
    except Exception:
        print("[WARNING] 检查 Gangtise fund 版本失败\n")


if __name__ == "__main__":
    print("检查 gangtise-fund 相关配置")
    if not get_authorization_token():
        print("  无法检测到gangtise密钥环境变量或授权文件, gangtise-fund 无法正常工作")
    else:
        print("  检测到gangtise授权文件, gangtise-fund 可以正常工作")
    try:
        if check_version(large_version=False):
            print("  gangtise-fund 版本为最新")
        else:
            print("  gangtise-fund 版本不是最新, 建议进行更新")
    except Exception:
        print("  检查 gangtise-fund 版本失败")
    print(f"  gangtise-fund 工作文件目录: {gangtise_workspace_path}")
