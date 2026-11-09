# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-fund/scripts/indicator.py
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

from gangtise_core.skill_runtime import ThreadPoolExecutor
from gangtise_core.skill_runtime import GangtiseError, ValidationError

import json
import math
import os
import re
import sys
from datetime import date, timedelta
from io import TextIOWrapper
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from .security import resolve_or_error

from .utils import (
    get_authorization_token,
    get_headers_extra,
    INDICATOR_CROSS_SECTION_URL,
    INDICATOR_SEARCH_URL,
    INDICATOR_TIME_SERIES_URL,
    check_version,
    format_response,
    normalize_securities_arg,
    parse_str_list,
)
from gangtise_core.auth import get_authorization_headers

INDICATORS_FILE_HINT = (
    "可以删除行或编辑参数列，再通过--indicators-file参数读取文件查询指标代码和参数"
)
INDICATORS_SEARCH_FILE_HINT = INDICATORS_FILE_HINT
SEARCH_LIMIT = 5
SEARCH_MAX_LIMIT = 100
POINTS_PER_100_CELLS = 0.05
ROOT_PARAM_ALIASES: Dict[str, str] = {
    "量纲": "scale",
    "日期类型": "calendarType",
}
# 历史文档误写 adjustmentType；接口实际参数名为 adjustType
PARAM_KEY_ALIASES: Dict[str, str] = {
    "adjustmentType": "adjustType",
    "adjustmenttype": "adjustType",
    "复权方式": "adjustType",
    "复权类型": "adjustType",
}
ROOT_PARAM_KEYS = frozenset({"scale", "calendarType", "currency"})
CALENDAR_TYPE_VALUES: Dict[str, str] = {
    "ND": "ND",
    "nd": "ND",
    "自然日": "ND",
    "TD": "TD",
    "td": "TD",
    "交易日": "TD",
    "WD": "WD",
    "wd": "WD",
    "工作日": "WD",
    "RD": "RD",
    "rd": "RD",
    "报告期": "RD",
}
CALENDAR_AXIS_LABEL = {"ND": "自然日", "TD": "交易日", "WD": "工作日", "RD": "报告期"}
SCALE_VALUES: Dict[str, str] = {
    "0": "0",
    "个": "0",
    "3": "3",
    "千": "3",
    "4": "4",
    "万": "4",
    "6": "6",
    "百万": "6",
    "8": "8",
    "亿": "8",
    "9": "9",
    "十亿": "9",
}


def _api_error_message(body: dict, fallback: str = "") -> str:
    if isinstance(body, dict):
        return str(body.get("msg") or body.get("message") or fallback)
    return fallback


def _load_indicators_from_file(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"指标文件不存在: {path}")
    df = pd.read_csv(path)
    code_col = None
    for col in ("indicator_code", "indicatorCode", "indicator_code_list"):
        if col in df.columns:
            code_col = col
            break
    if code_col is None:
        raise ValueError("指标文件须包含 indicator_code 或 indicatorCode 列")
    name_col = "indicator_name" if "indicator_name" in df.columns else (
        "indicatorName" if "indicatorName" in df.columns else None
    )
    has_params = "indicator_params" in df.columns
    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        code = str(row.get(code_col, "")).strip()
        if not code or code.lower() == "nan":
            continue
        name = str(row.get(name_col, "")).strip() if name_col else code
        if name.lower() == "nan":
            name = code
        params = _parse_indicator_params_cell(row.get("indicator_params")) if has_params else {}
        records.append({"code": code, "name": name, "params": params})
    if not records:
        raise ValueError("指标文件未解析到有效指标行")
    return records


def _parse_indicator_params_cell(raw: Any) -> Dict[str, Any]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return {}
    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return {}
    try:
        from json_repair import repair_json
        obj = repair_json(text, return_objects=True)
    except Exception:
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return {}
    return obj if isinstance(obj, dict) else {}


def _normalize_params_input(params: Any) -> Dict[str, Any]:
    """将 params 入参统一转为 dict。MCP 传输层可能以 JSON 字符串形式传递。"""
    if params is None:
        return {}
    if isinstance(params, dict):
        return params
    if isinstance(params, str):
        text = params.strip()
        if not text:
            return {}
        try:
            from json_repair import repair_json
            obj = repair_json(text, return_objects=True)
        except Exception:
            try:
                obj = json.loads(text)
            except json.JSONDecodeError as e:
                raise ValueError(f"params 须为合法 JSON: {e}") from e
        if not isinstance(obj, dict):
            raise ValueError("params 须为 JSON 对象（字典）")
        return obj
    return {}


def _default_indicator_params_from_item(item: dict) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    for p in item.get("parameterList") or []:
        if not isinstance(p, dict):
            continue
        pk = p.get("paramKey")
        dv = p.get("defaultValue")
        if pk is None or dv is None:
            continue
        dv_text = str(dv).strip()
        if not dv_text or dv_text == "—":
            continue
        params[str(pk)] = dv
    return params


def _search_items_to_config_records(items: List[dict]) -> List[dict]:
    records: List[dict] = []
    for item in items:
        code = str(item.get("indicatorCode", "")).strip()
        if not code:
            continue
        name = str(item.get("indicatorName", "")).strip()
        params = _default_indicator_params_from_item(item)
        records.append(
            {
                "indicator_code": code,
                "indicator_name": name,
                "indicator_params": json.dumps(params, ensure_ascii=False),
            }
        )
    return records


def _params_dict_from_file_entries(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for entry in entries:
        params = entry.get("params")
        if isinstance(params, dict) and params:
            out[str(entry["code"])] = params
    return out


def _merge_param_dicts(base: Dict[str, Any], override: Dict[str, Any], indicator_codes: List[str]) -> Dict[str, Any]:
    """合并参数字典，override（-p）优先于 base（indicators-file）。"""
    result: Dict[str, Any] = dict(base)
    code_set = set(indicator_codes)
    for key, val in override.items():
        if key in code_set and isinstance(val, dict):
            if key in result and isinstance(result[key], dict):
                result[key] = {**result[key], **val}
            else:
                result[key] = val
        else:
            result[key] = val
    return result


_YEAR_FIRST_DATE = re.compile(r"^(\d{4})([-/]?)(\d{2})\2(\d{2})$")


def _parse_date_param(value: Any, name: str) -> str:
    """年在前的日期（yyyy-MM-dd / yyyy/MM/dd / yyyyMMdd）统一为 yyyy-MM-dd；年在后或不存在的日期直接拒绝。"""
    text = str(value if value is not None else "").strip()
    m = _YEAR_FIRST_DATE.match(text)
    if not m:
        raise ValidationError(
            f"{name} 日期格式无效：「{text}」。请用 yyyy-MM-dd（也接受 yyyy/MM/dd、yyyyMMdd）；"
            "不接受年在后的写法，接口会按月在前解读（01-07-2026 被当成 1 月 7 日）"
        )
    normalized = f"{m.group(1)}-{m.group(3)}-{m.group(4)}"
    try:
        date.fromisoformat(normalized)
    except ValueError:
        raise ValidationError(f"{name}「{text}」不是真实存在的日期") from None
    return normalized


def _default_dates(
    start_date: Optional[str],
    end_date: Optional[str],
) -> Tuple[str, str]:
    if not end_date:
        end_date = date.today().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    return _parse_date_param(start_date, "开始日期"), _parse_date_param(end_date, "结束日期")


def _normalize_param_value(key: str, value: Any, where: str) -> Any:
    if isinstance(key, str) and key.lower().endswith("date") and not isinstance(value, (dict, list)):
        return _parse_date_param(value, f"{where}{key}")
    return value


def _date_span_days(start_date: str, end_date: str) -> int:
    s = date.fromisoformat(start_date[:10])
    e = date.fromisoformat(end_date[:10])
    return max(0, (e - s).days) + 1


def _parse_params_arg(raw: Optional[str]) -> Dict[str, Any]:
    if not raw or not str(raw).strip():
        return {}
    text = str(raw).strip()
    try:
        from json_repair import repair_json
        obj = repair_json(text, return_objects=True)
    except:
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"--params 须为合法 JSON 字典: {e}") from e
    if not isinstance(obj, dict):
        raise ValueError("--params 须为 JSON 对象（字典）")
    return obj


def _build_request_options(
    params: Dict[str, Any],
    indicator_codes: List[str],
) -> Tuple[Dict[str, Any], Optional[List[dict]]]:
    """将 -p 字典拆为根级参数与 indicatorParamList。

    根级仅 scale、calendarType 进入请求体顶层；其余标量键（如 adjustType）
    作为共享指标参数应用到本次全部指标；也可按指标编码嵌套覆盖，如
    {"adjustType":"3","qte_close":{"adjustType":"1"}}。
    """
    root_keys = {"scale", "calendarType", "currency"}
    root: Dict[str, Any] = {}
    nested_by_code: Dict[str, Dict[str, Any]] = {}
    shared_params: Dict[str, Any] = {}

    for key, val in params.items():
        if key in root_keys:
            root[key] = str(val)
        elif key in indicator_codes and isinstance(val, dict):
            nested_by_code[key] = {k: _normalize_param_value(k, v, f"{key} 的参数 ") for k, v in val.items()}
        elif isinstance(val, dict):
            raise ValidationError(
                f"参数引用了指标「{key}」，但它不在本次查询的指标列表（{', '.join(indicator_codes)}）中；"
                "按指标设参数时键须为本次查询的指标代码，拼错会导致参数静默不生效"
            )
        elif not isinstance(val, list):
            shared_params[key] = _normalize_param_value(key, val, "参数 ")

    per_indicator: List[dict] = []
    for code in indicator_codes:
        merged: Dict[str, Any] = dict(shared_params)
        merged.update(nested_by_code.get(code, {}))
        parameters = [
            {"paramKey": str(pk), "paramValue": str(pv)}
            for pk, pv in merged.items()
            if pk not in root_keys
        ]
        if parameters:
            per_indicator.append({"indicatorCode": code, "parameters": parameters})
    return root, per_indicator or None


def _register_indicator_aliases(
    alias_map: Dict[str, str],
    matches: List[Tuple[str, str, str]],
    token: str,
    code: str,
    name: str,
) -> None:
    alias_map[token] = code
    if name:
        alias_map[name] = code
    alias_map[code] = code
    alias_map[code.lower()] = code
    matches.append((token, code, name or code))


def _format_indicator_match_comment(matches: List[Tuple[str, str, str]]) -> str:
    if not matches:
        return ""
    parts: List[str] = []
    for token, code, name in matches:
        if token == code or token.lower() == code.lower():
            parts.append(code)
        else:
            label = name if name and name != code else token
            parts.append(f"{label}({code})")
    return f"<!-- 匹配到的指标：{', '.join(parts)} -->\n"


def _register_param_aliases(param_alias_map: Dict[str, str], param_key: str, param_name: str) -> None:
    pk = (param_key or "").strip()
    pn = (param_name or "").strip()
    if pk:
        param_alias_map[pk] = pk
        param_alias_map[pk.lower()] = pk
    if pn:
        param_alias_map[pn] = pk


def _register_param_aliases_from_item(param_alias_map: Dict[str, str], item: dict) -> None:
    for p in item.get("parameterList") or []:
        if not isinstance(p, dict):
            continue
        _register_param_aliases(
            param_alias_map,
            str(p.get("paramKey", "")),
            str(p.get("paramName", "")),
        )


def _resolve_param_key(key: str, param_alias_map: Dict[str, str]) -> str:
    if key in ROOT_PARAM_ALIASES:
        return ROOT_PARAM_ALIASES[key]
    if key in ROOT_PARAM_KEYS:
        return key
    if key in PARAM_KEY_ALIASES:
        return PARAM_KEY_ALIASES[key]
    if isinstance(key, str) and key.lower() in PARAM_KEY_ALIASES:
        return PARAM_KEY_ALIASES[key.lower()]
    mapped = param_alias_map.get(key)
    if mapped is None and isinstance(key, str):
        mapped = param_alias_map.get(key.lower())
    return mapped if mapped else key


def _normalize_root_param_value(param_key: str, value: Any) -> str:
    text = str(value).strip()
    if param_key == "calendarType":
        return CALENDAR_TYPE_VALUES.get(text, CALENDAR_TYPE_VALUES.get(text.lower(), text))
    if param_key == "scale":
        return SCALE_VALUES.get(text, text)
    return text


def _normalize_param_value_dict(val: Dict[str, Any], param_alias_map: Dict[str, str]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key, inner in val.items():
        nk = _resolve_param_key(key, param_alias_map)
        if nk in normalized and isinstance(normalized[nk], dict) and isinstance(inner, dict):
            normalized[nk] = {**normalized[nk], **_normalize_param_value_dict(inner, param_alias_map)}
        else:
            normalized[nk] = (
                _normalize_param_value_dict(inner, param_alias_map) if isinstance(inner, dict) else inner
            )
    return normalized


def _normalize_params_keys(
    params: Dict[str, Any],
    indicator_alias_map: Dict[str, str],
    param_alias_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """将 -p 中指标名/参数名的中文键替换为编码。"""
    merged_param_aliases: Dict[str, str] = dict(param_alias_map or {})
    normalized: Dict[str, Any] = {}

    def resolve_indicator_key(key: str) -> Optional[str]:
        code = indicator_alias_map.get(key)
        if code is None and isinstance(key, str):
            code = indicator_alias_map.get(key.lower())
        return code

    for key, val in params.items():
        param_key = _resolve_param_key(key, merged_param_aliases)
        if param_key in ROOT_PARAM_KEYS:
            normalized[param_key] = _normalize_root_param_value(param_key, val)
            continue

        indicator_code = resolve_indicator_key(key)
        if indicator_code and isinstance(val, dict):
            nested = _normalize_param_value_dict(val, merged_param_aliases)
            if indicator_code in normalized and isinstance(normalized[indicator_code], dict):
                normalized[indicator_code] = {**normalized[indicator_code], **nested}
            else:
                normalized[indicator_code] = nested
            continue

        if indicator_code:
            normalized[indicator_code] = val
            continue

        if param_key != key or key in merged_param_aliases or key in ROOT_PARAM_ALIASES:
            if isinstance(val, dict):
                nested = _normalize_param_value_dict(val, merged_param_aliases)
                if param_key in normalized and isinstance(normalized[param_key], dict):
                    normalized[param_key] = {**normalized[param_key], **nested}
                else:
                    normalized[param_key] = nested
            else:
                normalized[param_key] = val
            continue

        if isinstance(val, dict):
            normalized[key] = _normalize_param_value_dict(val, merged_param_aliases)
        else:
            normalized[key] = val
    return normalized


def _search_indicators(headers: dict, keyword: str, limit: int) -> Tuple[List[dict], Optional[str]]:
    from gangtise_core.skill_runtime import GangtiseError
    from gangtise_core.skill_runtime import request_json

    req_limit = max(1, min(int(limit), SEARCH_MAX_LIMIT))
    payload = {"keyword": keyword.strip(), "limit": req_limit}
    try:
        data = request_json("POST", INDICATOR_SEARCH_URL, json=payload, timeout=120)
    except GangtiseError:
        raise
    except Exception as e:
        return [], f"指标检索请求失败: {e}"
    if not isinstance(data, list):
        return [], "指标检索返回 data 格式异常"
    return data, None


def _exact_match_items(keyword: str, items: List[dict]) -> List[dict]:
    kw = keyword.strip()
    kw_lower = kw.lower()
    return [
        x
        for x in items
        if str(x.get("indicatorName", "")).strip() == kw
        or str(x.get("indicatorCode", "")).strip().lower() == kw_lower
    ]


def _filter_search_results(keyword: str, items: List[dict]) -> List[dict]:
    exact = _exact_match_items(keyword, items)
    return exact if exact else items


def _is_indicators_arg_codes(raw: str) -> bool:
    s = (raw or "").strip()
    return bool(s) and re.fullmatch(r"[a-zA-Z,，0-9]+", s) is not None


def _resolve_indicators_from_arg(
    headers: dict, raw: str
) -> Tuple[
    Optional[List[str]],
    Optional[str],
    Optional[str],
    Dict[str, str],
    List[Tuple[str, str, str]],
    Dict[str, str],
    List[Dict[str, Any]],
]:
    """将 --indicators 解析为指标编码。返回 (codes, search_md, error, alias_map, matches, param_alias_map, indicator_meta)。"""
    alias_map: Dict[str, str] = {}
    matches: List[Tuple[str, str, str]] = []
    param_alias_map: Dict[str, str] = {}
    indicator_meta: List[Dict[str, Any]] = []
    if _is_indicators_arg_codes(raw):
        codes = parse_str_list(raw)
        for code in codes:
            _register_indicator_aliases(alias_map, matches, code, code, code)
            indicator_meta.append({"code": code, "name": code, "params": {}})
        return codes, None, None, alias_map, matches, param_alias_map, indicator_meta

    resolved: List[str] = []
    for token in parse_str_list(raw):
        items, err = _search_indicators(headers, token, SEARCH_LIMIT)
        if err:
            return None, None, err, {}, [], {}, []
        if not items:
            return None, None, f"未找到与「{token}」相关的基金指标", {}, [], {}, []
        exact = _exact_match_items(token, items)
        if len(exact) == 1:
            item = exact[0]
            code = str(item["indicatorCode"])
            name = str(item.get("indicatorName", "")).strip()
            resolved.append(code)
            _register_indicator_aliases(alias_map, matches, token, code, name)
            _register_param_aliases_from_item(param_alias_map, item)
            indicator_meta.append(
                {
                    "code": code,
                    "name": name or code,
                    "params": _default_indicator_params_from_item(item),
                    "data_type": _data_type_from_search_item(item),
                }
            )
            continue
        display = exact if exact else items
        exact_only = bool(exact)
        if len(exact) > 1:
            prefix = f"「{token}」存在 {len(exact)} 条完全匹配，请指定更精确的指标：\n\n"
        else:
            prefix = f"未找到与「{token}」完全匹配的指标，以下为候选结果：\n\n"
        return None, prefix + _items_to_markdown(token, display, exact_only), None, {}, [], {}, []
    return resolved, None, None, alias_map, matches, param_alias_map, indicator_meta


def _format_scope_list(scope_list: Optional[List[dict]]) -> str:
    if not scope_list:
        return "—"
    parts = []
    for s in scope_list:
        if not isinstance(s, dict):
            continue
        market = s.get("market") or ""
        st = s.get("securityType") or ""
        label = " / ".join(x for x in (market, st) if x)
        restriction = s.get("usageRestriction")
        if restriction and str(restriction).strip() and str(restriction).strip().lower() != "null":
            label = f"{label}（{str(restriction).strip()}）" if label else str(restriction).strip()
        if label:
            parts.append(label)
    return "；".join(parts) if parts else "—"


def _format_parameter_list(param_list: Optional[List[dict]]) -> str:
    if not param_list:
        return "_无额外参数_"
    lines = [
        "| 参数编码 | 参数名称 | 类型 | 必填 | 默认值 | 说明 | 枚举 |",
        "| - | - | - | - | - | - | - |",
    ]
    for p in param_list:
        if not isinstance(p, dict):
            continue
        enums = p.get("enumList") or []
        enum_text = "；".join(
            f"{e.get('label', '')}={e.get('value', '')}"
            for e in enums
            if isinstance(e, dict)
        ) or "—"
        lines.append(
            "| {paramKey} | {paramName} | {paramType} | {required} | {defaultValue} | {paramDescription} | {enum} |".format(
                paramKey=p.get("paramKey", ""),
                paramName=p.get("paramName", ""),
                paramType=p.get("paramType", ""),
                required="是" if p.get("required") else "否",
                defaultValue=p.get("defaultValue", "") if p.get("defaultValue") is not None else "—",
                paramDescription=(p.get("paramDescription") or "—").replace("\n", " "),
                enum=enum_text,
            )
        )
    return "\n".join(lines)


def _indicator_item_to_markdown(item: dict, index: int) -> str:
    code = item.get("indicatorCode", "")
    name = item.get("indicatorName", "")
    score = item.get("score", "")
    desc = (item.get("description") or "—").strip()
    scope = _format_scope_list(item.get("scopeList"))
    params_md = _format_parameter_list(item.get("parameterList"))
    return (
        f"### {index}. {name} (`{code}`)\n\n"
        f"- **相关度得分**：{score}\n"
        f"- **适用范围**：{scope}\n"
        f"- **算法说明**：{desc}\n\n"
        f"**请求参数**\n\n{params_md}\n"
    )


def _items_to_markdown(keyword: str, items: List[dict], exact_only: bool) -> str:
    head = f"## 基金指标检索：「{keyword}」\n\n"
    if exact_only:
        head += f"共 {len(items)} 条**完全匹配**结果。\n\n"
    else:
        head += f"展示前 {len(items)} 条相关结果（无完全匹配时返回全部检索命中）。\n\n"
    body = "\n".join(_indicator_item_to_markdown(it, i + 1) for i, it in enumerate(items))
    return head + body


def _post_indicator_api(url: str, headers: dict, payload: dict) -> Tuple[Optional[dict], Optional[str]]:
    from gangtise_core.skill_runtime import request_json

    try:
        data = request_json("POST", url, json=payload, timeout=300)
    except GangtiseError:
        raise
    except Exception as e:
        return None, f"请求失败: {e}"
    return {"code": "000000", "status": True, "data": data}, None


def _count_value_cells(block: dict) -> int:
    values = block.get("values") or []
    total = 0
    for row in values:
        if isinstance(row, list):
            total += len(row)
    return total


def _is_string_data_type(data_type: Any) -> bool:
    if data_type is None:
        return False
    return str(data_type).strip().lower() in {"string", "str", "text", "varchar"}


def _indicator_data_types(block: dict, ind_codes: List[Any]) -> List[str]:
    raw = block.get("dataTypes") or block.get("dataTypeList") or []
    if not isinstance(raw, list):
        return [""] * len(ind_codes)
    return [str(t).strip() if t is not None else "" for t in raw] + [""] * max(0, len(ind_codes) - len(raw))


def _data_type_from_search_item(item: dict) -> str:
    for key in ("dataType", "dataTypes", "valueType"):
        val = item.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def _coerce_indicator_values(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data
    work = data.copy()
    if "data_type" in work.columns:
        string_mask = work["data_type"].map(_is_string_data_type).fillna(False)
        work = work.drop(columns=["data_type"])
    else:
        string_mask = pd.Series(False, index=work.index)

    parts: List[pd.DataFrame] = []
    num_mask = ~string_mask
    if num_mask.any():
        num_df = work.loc[num_mask].copy()
        num_df["value"] = pd.to_numeric(num_df["value"], errors="coerce")
        num_df = num_df.dropna(subset=["value"])
        parts.append(num_df)
    if string_mask.any():
        str_df = work.loc[string_mask].copy()
        str_df["value"] = str_df["value"].map(
            lambda v: None if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip() or None
        )
        str_df = str_df.dropna(subset=["value"])
        parts.append(str_df)
    if not parts:
        return work.iloc[0:0]
    return pd.concat(parts, ignore_index=True)


def _fill_indicator_data_types(data: pd.DataFrame, indicator_meta: Optional[List[Dict[str, Any]]]) -> pd.DataFrame:
    type_by_code = {
        str(m["code"]): str(m.get("data_type") or "").strip()
        for m in (indicator_meta or [])
        if m.get("code")
    }
    if not type_by_code:
        return data
    work = data.copy()
    if "data_type" not in work.columns:
        work["data_type"] = work["indicator_code"].map(type_by_code).fillna("")
    else:
        missing = work["data_type"].isna() | (work["data_type"].astype(str).str.strip() == "")
        work.loc[missing, "data_type"] = work.loc[missing, "indicator_code"].map(type_by_code).fillna("")
    return work


def _parse_timeseries_block(block: dict) -> pd.DataFrame:
    dates = block.get("dates") or []
    codes = block.get("securityCodeList") or []
    names = block.get("securityNameList") or []
    indicator_list = block.get("indicatorList") or []
    if indicator_list:
        ind_codes = [str(i.get("code", "")) for i in indicator_list]
        ind_names = [str(i.get("name", "")) for i in indicator_list]
        ind_types = [str(i.get("dataType", "")) for i in indicator_list]
    else:
        ind_codes = block.get("indicatorCodeList") or []
        ind_names = block.get("indicatorNameList") or []
        ind_types = _indicator_data_types(block, ind_codes)
    values = block.get("values") or []
    records: List[dict] = []

    if len(codes) == 1 and len(ind_codes) >= 1:
        sec = str(codes[0])
        sec_name = str(names[0]) if names else ""
        for i, ind_c in enumerate(ind_codes):
            ind_n = str(ind_names[i]) if i < len(ind_names) else str(ind_c)
            ind_type = ind_types[i] if i < len(ind_types) else ""
            row_vals = values[i] if i < len(values) else []
            for j, d in enumerate(dates):
                records.append(
                    {
                        "security_code": sec,
                        "security_name": sec_name,
                        "indicator_code": str(ind_c),
                        "indicator_name": ind_n,
                        "data_type": ind_type,
                        "date": str(d)[:10],
                        "value": row_vals[j] if j < len(row_vals) else None,
                    }
                )
    elif len(ind_codes) == 1 and len(codes) >= 1:
        ind_c = str(ind_codes[0])
        ind_n = str(ind_names[0]) if ind_names else ind_c
        ind_type = ind_types[0] if ind_types else ""
        for i, sec in enumerate(codes):
            sec_name = str(names[i]) if i < len(names) else ""
            row_vals = values[i] if i < len(values) else []
            for j, d in enumerate(dates):
                records.append(
                    {
                        "security_code": str(sec),
                        "security_name": sec_name,
                        "indicator_code": ind_c,
                        "indicator_name": ind_n,
                        "data_type": ind_type,
                        "date": str(d)[:10],
                        "value": row_vals[j] if j < len(row_vals) else None,
                    }
                )
    return pd.DataFrame(records)


def _parse_cross_section_block(block: dict) -> pd.DataFrame:
    dt = str(block.get("date", ""))[:10]
    codes = block.get("securityCodeList") or []
    names = block.get("securityNameList") or []
    indicator_list = block.get("indicatorList") or []
    if indicator_list:
        ind_codes = [str(i.get("code", "")) for i in indicator_list]
        ind_names = [str(i.get("name", "")) for i in indicator_list]
        ind_types = [str(i.get("dataType", "")) for i in indicator_list]
    else:
        ind_codes = block.get("indicatorCodeList") or []
        ind_names = block.get("indicatorNameList") or []
        ind_types = _indicator_data_types(block, ind_codes)
    values = block.get("values") or []
    records: List[dict] = []
    for i, ind_c in enumerate(ind_codes):
        ind_n = str(ind_names[i]) if i < len(ind_names) else str(ind_c)
        ind_type = ind_types[i] if i < len(ind_types) else ""
        row = values[i] if i < len(values) else []
        for j, sec in enumerate(codes):
            records.append(
                {
                    "date": dt,
                    "security_code": str(sec),
                    "security_name": str(names[j]) if j < len(names) else "",
                    "indicator_code": str(ind_c),
                    "indicator_name": ind_n,
                    "data_type": ind_type,
                    "value": row[j] if j < len(row) else None,
                }
            )
    return pd.DataFrame(records)


def _usage_from_cells(cell_count: int) -> float:
    if cell_count <= 0:
        return 0.0
    return math.ceil(cell_count / 100) * POINTS_PER_100_CELLS


FISCAL_YEAR_FALLBACK_CODES = frozenset({"div_cash_yr", "div_cash_paid_ratio"})


def _lookup_indicator_items(headers: dict, codes: List[str]) -> Dict[str, Optional[dict]]:
    """按指标代码逐个检索并取完全匹配项；检索失败或无匹配记为 None。"""

    def one(code: str) -> Tuple[str, Optional[dict]]:
        try:
            items, err = _search_indicators(headers, code, SEARCH_MAX_LIMIT)
        except Exception:
            return code, None
        if err:
            return code, None
        for item in items:
            if isinstance(item, dict) and str(item.get("indicatorCode", "")) == code:
                return code, item
        return code, None

    unique = list(dict.fromkeys(c for c in codes if c))
    if not unique:
        return {}
    with ThreadPoolExecutor(max_workers=min(5, len(unique))) as ex:
        return dict(ex.map(one, unique))


def _param_keys(item: Optional[dict]) -> List[str]:
    if not item:
        return []
    return [str(p.get("paramKey")) for p in (item.get("parameterList") or []) if isinstance(p, dict) and p.get("paramKey")]


def _calendar_axis_label(calendar_type: Optional[str]) -> str:
    """未传 calendarType 时，日期轴由服务端按指标决定。"""
    if not calendar_type:
        return "按指标自动"
    return CALENDAR_AXIS_LABEL.get(str(calendar_type), str(calendar_type))


def _missing_fiscal_year(
    items: Dict[str, Optional[dict]],
    codes: List[str],
    indicator_param_list: Optional[List[dict]],
) -> List[str]:
    given = {
        str(group.get("indicatorCode")): {str(p.get("paramKey")) for p in group.get("parameters") or []}
        for group in indicator_param_list or []
    }
    out: List[str] = []
    for code in codes:
        item = items.get(code)
        needs = "fiscalYear" in _param_keys(item) if item else (
            code.startswith("frcst_") or code in FISCAL_YEAR_FALLBACK_CODES
        )
        if needs and "fiscalYear" not in given.get(code, set()):
            out.append(code)
    return out


def _resolve_security_codes(headers: dict, tokens: List[str], output_dir: Optional[str]):
    """只接受基金。成功返回 (codes, warning, None)，失败返回 ([], None, 错误输出)。"""
    codes, _abbrs, notes, err = resolve_or_error(tokens, headers, "indicator", output_dir)
    if err is not None:
        return [], None, err
    out = []
    for code in codes or []:
        cu = str(code).strip().upper()
        if cu and cu not in out:
            out.append(cu)
    note = "\n".join(notes) if notes else None
    return out, note, None


def indicator_search(keyword: str,
    output_dir: Optional[str] = None,
):
    usage: dict = {}
    if get_authorization_token() is None:
        return format_response(
            {
                "state": "error",
                "message": "未配置 gangtise 授权，无法调用 open 接口",
                "data": [],
                "usage": usage,
            },
            "indicator", output_dir=output_dir)
    kw = (keyword or "").strip()
    if not kw:
        return format_response(
            {"state": "error", "message": "keyword 不能为空", "data": [], "usage": usage},
            "indicator", output_dir=output_dir)
    headers = get_authorization_headers()
    items, err = _search_indicators(headers, kw, SEARCH_LIMIT)
    if err:
        return format_response(
            {"state": "error", "message": err, "data": [], "usage": usage},
            "indicator", output_dir=output_dir)
    if not items:
        return format_response(
            {
                "state": "error",
                "message": f"未找到与「{kw}」相关的基金指标",
                "data": [],
                "usage": usage,
            },
            "indicator", output_dir=output_dir)
    before_filter = items
    items = _filter_search_results(kw, items)
    exact_only = len(items) < len(before_filter)

    records = _search_items_to_config_records(items)
    if not records:
        return format_response(
            {
                "state": "error",
                "message": f"未找到与「{kw}」相关的基金指标",
                "data": [],
                "usage": usage,
            },
            "indicator", output_dir=output_dir)
    if exact_only:
        msg = f"共 {len(records)} 条与「{kw}」完全匹配的基金指标"
    else:
        msg = f"已检索到 {len(records)} 条与「{kw}」相关的基金指标"
    parts = [
        {
            "data": records,
            "module": "company_indicator_search",
            "type": "data",
            "footer": INDICATORS_SEARCH_FILE_HINT,
        }
    ]
    return format_response(
        {
            "state": "success",
            "message": msg,
            "data": parts,
            "usage": usage,
        },
        "indicator", output_dir=output_dir)


def indicator_get(
    indicator_codes: List[str],
    securities: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    indicator_meta: Optional[List[Dict[str, Any]]] = None,
    output_dir: Optional[str] = None,
):
    usage: dict = {}
    if get_authorization_token() is None:
        return format_response(
            {
                "state": "error",
                "message": "未配置 gangtise 授权，无法调用 open 接口",
                "data": [],
                "usage": usage,
            },
            "indicator", output_dir=output_dir)

    indicators = [str(x).strip() for x in indicator_codes if str(x).strip()]
    if not indicators:
        return format_response(
            {"state": "error", "message": "indicatorCodeList 不能为空", "data": [], "usage": usage},
            "indicator", output_dir=output_dir)
    tokens = normalize_securities_arg(securities) or []
    if not tokens:
        return format_response(
            {
                "state": "error",
                "message": "请指定 --securities",
                "data": [],
                "usage": usage,
            },
            "indicator", output_dir=output_dir)

    start_date, end_date = _default_dates(start_date, end_date)
    headers = get_authorization_headers()

    codes, usage_note, resolve_err = _resolve_security_codes(headers, tokens, output_dir)
    if resolve_err is not None:
        return resolve_err
    if not codes:
        msg = usage_note or "未解析到有效基金代码"
        return format_response(
            {"state": "error", "message": msg, "data": [], "usage": usage},
            "indicator", output_dir=output_dir)

    param_dict = _normalize_params_keys(_normalize_params_input(params), {}, {})
    root_opts, indicator_param_list = _build_request_options(param_dict, indicators)

    frames: List[pd.DataFrame] = []
    errors: List[str] = []
    total_cells = 0

    indicator_items = _lookup_indicator_items(headers, indicators)
    # 不传时服务端按指标返回交易日、报告期或两者并集；只有显式传入才固定日期类型。
    calendar_type = root_opts.get("calendarType") or None
    base_payload: Dict[str, Any] = {
        "startDate": start_date,
        "endDate": end_date,
        "currency": root_opts.get("currency", "DFT"),
        "scale": root_opts.get("scale", "0"),
        "indicatorParamList": indicator_param_list if indicator_param_list is not None else [],
    }
    if calendar_type:
        base_payload["calendarType"] = calendar_type
    no_fiscal_year = _missing_fiscal_year(indicator_items, indicators, indicator_param_list)

    if len(codes) > len(indicators):
        for ind in indicators:
            payload = {
                **base_payload,
                "indicatorCodeList": [ind],
                "universe": codes,
            }
            body, err = _post_indicator_api(INDICATOR_TIME_SERIES_URL, headers, payload)
            if err:
                errors.append(f"{ind}: {err}")
                continue
            block = body.get("data") or {}
            total_cells += _count_value_cells(block)
            df_part = _parse_timeseries_block(block)
            if not df_part.empty:
                frames.append(df_part)
    else:
        for sec in codes:
            payload = {
                **base_payload,
                "indicatorCodeList": indicators,
                "universe": [sec],
            }
            body, err = _post_indicator_api(INDICATOR_TIME_SERIES_URL, headers, payload)
            if err:
                errors.append(f"{sec}: {err}")
                continue
            block = body.get("data") or {}
            total_cells += _count_value_cells(block)
            df_part = _parse_timeseries_block(block)
            if not df_part.empty:
                frames.append(df_part)
    api_label = "时序"

    if not frames:
        err_tail = "；".join(errors) if errors else "未获取到指标数据"
        return format_response(
            {"state": "error", "message": err_tail, "data": [], "usage": usage},
            "indicator", output_dir=output_dir)

    data = pd.concat(frames, ignore_index=True)
    data = _fill_indicator_data_types(data, indicator_meta)
    data = _coerce_indicator_values(data)
    data = data.sort_values(
        by=["security_code", "indicator_code", "date"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    if data.empty:
        err_tail = "；".join(errors) if errors else "指标数据均为空值"
        return format_response(
            {"state": "error", "message": err_tail, "data": [], "usage": usage},
            "indicator", output_dir=output_dir)

    if total_cells > 0:
        usage["ede_indicator_get"] = usage.get("ede_indicator_get", 0) + _usage_from_cells(total_cells)

    title = f"{len(indicators)} 个指标 × {len(codes)} 只证券"
    axis = _calendar_axis_label(calendar_type)
    msg = f"已获取{title}{api_label}数据（{start_date} 至 {end_date}，日期轴：{axis}）"
    if usage_note:
        msg += f"\n{usage_note}"
    if no_fiscal_year:
        msg += (
            f"\n[WARNING]{'、'.join(no_fiscal_year)} 需要 fiscalYear（预测/分红年度）参数但未传："
            '服务端漏传不报错，可能返回 null 或默认年度的值；请按指标传入，如 {"' + no_fiscal_year[0] + '": {"fiscalYear": "2025"}}'
        )
    if errors:
        msg += f"\n部分请求异常：{'；'.join(errors[:3])}"

    # get 成功只返回时序/截面数据；参数模板仅 search（company_indicator_search）产出
    parts = [
        {
            "data": data.to_dict(orient="records"),
            "module": "indicator",
            "type": "data",
        }
    ]
    response = {"state": "success", "message": msg, "data": parts, "usage": usage}
    if errors:
        response["partial"] = "；".join(errors[:3])
    return format_response(response, "indicator", output_dir=output_dir)


def fund_indicator(
    keyword: Optional[str] = None,
    indicator_codes: Optional[str] = None,
    securities: Optional[Any] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    output_dir: Optional[str] = None,
):
    """检索基金指标元信息，或在提供 indicator_codes + securities 时拉取时序/截面数据。

    优先级：有 indicator_codes → get；否则有 keyword → search。
    仅有 securities 不会进入 get。
    """
    indicators_raw = (indicator_codes or "").strip()
    sec_list = normalize_securities_arg(securities)

    if indicators_raw:
        if not sec_list:
            return format_response(
                {
                    "state": "error",
                    "message": "拉取数据须提供 securities",
                    "data": [],
                    "usage": {},
                },
                "indicator", output_dir=output_dir)
        if get_authorization_token() is None:
            return format_response(
                {
                    "state": "error",
                    "message": "未配置 gangtise 授权，无法调用 open 接口",
                    "data": [],
                    "usage": {},
                },
                "indicator", output_dir=output_dir)
        headers = get_authorization_headers()
        codes, search_md, err, indicator_aliases, indicator_matches, param_aliases, indicator_meta = (
            _resolve_indicators_from_arg(headers, indicators_raw)
        )
        if err:
            return format_response(
                {"state": "error", "message": err, "data": [], "usage": {}},
                "indicator", output_dir=output_dir)
        if search_md:
            return format_response(
                {
                    "state": "success",
                    "message": search_md,
                    "data": [],
                    "usage": {},
                },
                "indicator", output_dir=output_dir)
        try:
            param_dict = _normalize_params_keys(
                _normalize_params_input(params),
                indicator_aliases,
                param_aliases,
            )
        except ValueError as e:
            return format_response(
                {"state": "error", "message": str(e), "data": [], "usage": {}},
                "indicator", output_dir=output_dir)
        return indicator_get(
            indicator_codes=codes,
            securities=sec_list,
            start_date=start_date,
            end_date=end_date,
            params=param_dict,
            indicator_meta=indicator_meta,
            output_dir=output_dir,
        )

    kw = (keyword or "").strip()
    if kw:
        return indicator_search(kw, output_dir=output_dir)

    return format_response(
        {
            "state": "error",
            "message": "请提供 keyword 检索指标，或 indicator_codes + securities 拉取数据",
            "data": [],
            "usage": {},
        },
        "indicator", output_dir=output_dir)


def main():
    import argparse

    try:
        if not check_version():
            update_sh = os.path.join(script_dir, "update.sh")
            print(f"[WARNING] 存在 Gangtise fund 版本更新，可以执行 {update_sh} 更新，请与用户确认是否更新\n")
    except Exception:
        print("[WARNING] 检查 Gangtise fund 版本失败\n")

    today_str = date.today().strftime("%Y-%m-%d")
    default_start = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(
        description="基金指标（EDE）：检索指标元信息或拉取时序/截面数据",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["search", "get"],
        default="search",
        help="search=检索指标元信息（Markdown）；get=拉取指标数据（CSV）；提供 --indicators 时自动为 get",
    )
    parser.add_argument("-k", "--keyword", default="", help="检索关键词（search 模式）")
    parser.add_argument(
        "--indicators",
        default=None,
        help="指标编码或名称关键词，逗号分隔；提供后自动进入 get（纯英文字母与逗号视为编码，否则先检索）",
    )
    parser.add_argument(
        "--indicators-file",
        default=None,
        help="CSV 含 indicator_code、indicator_name、indicator_params 列（get 模式）",
    )
    parser.add_argument("--securities", default=None, help="证券：完整代码/名称/拼音等，逗号分隔；亦可传 .csv 路径（须含 security_code 等列）")
    parser.add_argument("-sd", "--start-date", default=None, help=f"开始日期 yyyy-MM-dd（get），默认 {default_start}")
    parser.add_argument("-ed", "--end-date", default=None, help=f"结束日期 yyyy-MM-dd（get），默认 {today_str}")
    parser.add_argument(
        "-p",
        "--params",
        default=None,
        help=(
            "指标参数字典 JSON：scale/量纲、calendarType/日期类型（ND 自然日、TD 交易日、WD 工作日、RD 报告期，支持中文）。"
            "不传 calendarType 时由服务端按指标返回日期序列。其余见 references/indicator.md"
        ),
    )
    parser.add_argument(
        "-od",
        "--output-dir",
        default=None,
        help="结果保存目录路径，建议使用绝对路径",
    )

    args = parser.parse_args()
    mode = (args.mode or "search").strip().lower()

    indicator_meta: List[Dict[str, Any]] = []
    indicators_raw = (args.indicators or "").strip() or None
    securities_raw = args.securities

    if args.indicators_file:
        try:
            indicator_meta = _load_indicators_from_file(args.indicators_file)
            indicators_raw = ",".join(str(x["code"]) for x in indicator_meta)
        except Exception as e:
            print(f"解析指标文件失败: {e}")
            sys.exit(1)
    # 优先级：--indicators / --indicators-file → get；否则 -m get 缺参报错；否则 -k → search
    # （单独 --securities 不会进入 get，避免 -k + --securities 被误判）
    if indicators_raw:
        param_dict: Dict[str, Any] = {}
        if args.params:
            try:
                param_dict = _parse_params_arg(args.params)
            except Exception as e:
                parser.error(str(e))
        if indicator_meta:
            try:
                sec_list = normalize_securities_arg(securities_raw)
            except Exception as e:
                print(f"解析 --securities 失败: {e}")
                sys.exit(1)
            if not sec_list:
                parser.error("拉取数据须提供 --securities（代码/名称，或 .csv 路径）")
            codes = [str(x["code"]) for x in indicator_meta]
            file_params = _params_dict_from_file_entries(indicator_meta)
            try:
                param_dict = _merge_param_dicts(file_params, param_dict, codes)
            except Exception as e:
                parser.error(str(e))
            print(
                indicator_get(
                    indicator_codes=codes,
                    securities=sec_list,
                    start_date=args.start_date,
                    end_date=args.end_date,
                    params=param_dict,
                    indicator_meta=indicator_meta,
                )
            )
            return
        print(
            fund_indicator(
                indicator_codes=indicators_raw,
                securities=securities_raw,
                start_date=args.start_date,
                end_date=args.end_date,
                params=param_dict or None,
        output_dir=args.output_dir or None,
    )
        )
        return

    kw = (args.keyword or "").strip()
    if mode == "get":
        parser.error("拉取数据（-m get）须同时提供 --indicators/--indicators-file 与 --securities")
    if kw:
        print(indicator_search(kw,
        output_dir=args.output_dir or None,
    ))
        return
    if securities_raw:
        parser.error("拉取数据须同时提供 --indicators/--indicators-file；仅检索请用 -k/--keyword 或 -m search -k")
    parser.error("请提供 -k/--keyword（或 -m search -k）检索，或 --indicators/--indicators-file + --securities 拉取数据")


if __name__ == "__main__":
    encoding = "utf-8"
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding=encoding, errors="ignore")
    main()
