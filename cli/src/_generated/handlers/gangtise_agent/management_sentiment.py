# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-agent/scripts/management_sentiment.py
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
import os
import re
import sys
from io import TextIOWrapper
from typing import Any, Dict, List, Optional, Tuple

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from gangtise_core.auth import authorized_request, get_authorization_headers
from gangtise_core.skill_runtime import ValidationError
from .security import security_search_basic
from .utils import GANGTISE_OPENAI_DOMAIN, check_version, format_response

INDICATOR_URL = f"{GANGTISE_OPENAI_DOMAIN}/management-sentiment/company/indicator"
CONCLUSION_URL = f"{GANGTISE_OPENAI_DOMAIN}/management-sentiment/company/conclusion"
DETAIL_URL = f"{GANGTISE_OPENAI_DOMAIN}/management-sentiment/company/detail"

METHOD_NAME = "management_sentiment"
POINTS_PER_RECORD = 5
POINTS_PER_DETAIL_CALL = 10
PAGE_SIZE_MAX = 100
DEFAULT_PAGE_SIZE = {"indicator": 20, "conclusion": 10}

_TYPE_LABEL = {
    "indicator": "指标",
    "conclusion": "结论",
    "detail": "明细",
}
_TYPE_ALIASES = {
    "indicator": "indicator",
    "指标": "indicator",
    "conclusion": "conclusion",
    "结论": "conclusion",
    "detail": "detail",
    "明细": "detail",
}
_SOURCE_TYPE_LABEL = {"conference": "电话会议"}
_SOURCE_TYPE_ALIASES = {
    "conference": "conference",
    "电话会议": "conference",
    "会议": "conference",
}

_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
_CODE_PATTERN = re.compile(r"^(\d{6}|[A-Z]?\d+)\.[A-Z]{2,4}$")

_RESPONSIVENESS_LABEL = {5.0: "正面回应问题", 2.5: "部分回应问题", 0.0: "基本回避问题"}
_POLARITY_LABEL = {5.0: "乐观", 2.5: "中性", 0.0: "风险"}
_CONVICTION_LABEL = {5.0: "确定度较高", 2.5: "确定度中等", 0.0: "确定度较低"}


def normalize_sentiment_type(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    token = str(raw).strip()
    if not token:
        return None
    if token in _TYPE_ALIASES:
        return _TYPE_ALIASES[token]
    low = token.lower()
    return _TYPE_ALIASES.get(low)


def _as_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        items = raw
    else:
        items = str(raw).replace("，", ",").split(",")
    out: List[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
    return out


def _md_cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n")
    return " ".join(text.splitlines()).strip()


def _fmt_num(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{float(value):.2f}"
    return str(value)


def _score_with_label(value: Any, labels: Dict[float, str]) -> str:
    shown = _fmt_num(value)
    if shown == "":
        return ""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return shown
    for score, label in labels.items():
        if abs(num - score) < 1e-6:
            return f"{shown}（{label}）"
    return shown


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _validate_time(value: Optional[str], field_name: str, end_of_day: bool) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if _DATE_ONLY.match(text):
            datetime.datetime.strptime(text, "%Y-%m-%d")
            return f"{text} 23:59:59" if end_of_day else f"{text} 00:00:00"
        if _DATETIME.match(text):
            datetime.datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            return text
    except ValueError:
        pass
    raise ValueError(f"{field_name} 格式错误，仅支持 yyyy-MM-dd 或 yyyy-MM-dd HH:mm:ss")


def _source_line(source: Any, prefix: str = "来源") -> str:
    if not isinstance(source, dict):
        return ""
    source_type = _text(source.get("sourceType"))
    type_label = _SOURCE_TYPE_LABEL.get(source_type, source_type)
    source_id = _text(source.get("sourceId"))
    source_name = _text(source.get("sourceName"))
    publish = _text(source.get("publishTime"))
    bits = []
    if source_name:
        bits.append(source_name)
    if type_label or source_id:
        bits.append(f"{type_label or '-'} / {source_id or '-'}")
    if publish:
        bits.append(publish)
    if not bits:
        return ""
    return f"- **{prefix}**：{'；'.join(bits)}"


def _append_qa_block(lines: List[str], title: str, items: Any) -> None:
    lines.append(f"**{title}**")
    lines.append("")
    if not isinstance(items, list) or not items:
        lines.append("（无）")
        lines.append("")
        return
    for index, qa in enumerate(items, 1):
        if not isinstance(qa, dict):
            continue
        lines.append(f"{index}. {_text(qa.get('questionBrief')) or '（无简述）'}")
        lines.append(f"   - 回答节选：{_text(qa.get('answerQuote')) or '（无）'}")
        highlights = qa.get("highlight") if isinstance(qa.get("highlight"), list) else []
        if highlights:
            lines.append("   - 高亮：" + "、".join(_text(item) for item in highlights if _text(item)))
        q_trace = _text(qa.get("qTrace"))
        a_trace = _text(qa.get("aTrace"))
        if q_trace or a_trace:
            lines.append(f"   - 录音定位（毫秒）：提问 {q_trace or '-'}；回答 {a_trace or '-'}")
    lines.append("")


def markdown_indicator(data: Dict[str, Any], page_from: int) -> str:
    total = data.get("total", 0)
    rows = data.get("list") if isinstance(data.get("list"), list) else []
    lines = [f"## 管理层情绪指标（本页 {len(rows)} 条，接口 total={total}）", ""]
    if not rows:
        lines.append("未找到符合条件的管理层情绪指标。")
        return "\n".join(lines).strip()
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = _text(row.get("securityName"))
        code = _text(row.get("securityCode"))
        title = f"{name}（{code}）" if name and code else (name or code or "未知证券")
        lines.append(f"### {title}")
        lines.append(f"- **发布时间**：{_text(row.get('publishTime')) or '-'}")
        source_line = _source_line(row.get("source"))
        if source_line:
            lines.append(source_line)
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        source_type = _text(source.get("sourceType"))
        source_id = _text(source.get("sourceId"))
        if source_type and source_id:
            lines.append(f"- **取明细**：`--type detail --source-type {source_type} --source-id {source_id}`")
        lines.append("")
        lines.append("| 正面回应程度 | 回复乐观度 | 回复确定度 | 有效问答 | 回避占比(%) | 风险占比(%) | 不确定占比(%) |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(_fmt_num(row.get("sentimentResponsiveness"))),
                    _md_cell(_fmt_num(row.get("sentimentPolarity"))),
                    _md_cell(_fmt_num(row.get("sentimentConviction"))),
                    _md_cell(row.get("qaCount")),
                    _md_cell(_fmt_num(row.get("qaEvasionRatio"))),
                    _md_cell(_fmt_num(row.get("qaRiskRatio"))),
                    _md_cell(_fmt_num(row.get("qaUncertaintyRatio"))),
                ]
            )
            + " |"
        )
        lines.append("")
        categories = row.get("questionCategoryList") if isinstance(row.get("questionCategoryList"), list) else []
        if categories:
            lines.append("**分问题类型**")
            lines.append("")
            lines.append("| 问题类型 | 重要 | 问答条数 | 正面回应程度 | 回复乐观度 | 回复确定度 |")
            lines.append("| --- | --- | --- | --- | --- | --- |")
            for item in categories:
                if not isinstance(item, dict):
                    continue
                cat_name = _text(item.get("questionCategoryName")) or _text(item.get("questionCategory"))
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            _md_cell(cat_name),
                            _md_cell("是" if item.get("isImportant") else "否"),
                            _md_cell(item.get("questionCategoryQaCount")),
                            _md_cell(_fmt_num(item.get("questionCategoryResponsiveness"))),
                            _md_cell(_fmt_num(item.get("questionCategoryPolarity"))),
                            _md_cell(_fmt_num(item.get("questionCategoryConviction"))),
                        ]
                    )
                    + " |"
                )
            lines.append("")
        lines.append("---")
        lines.append("")
    _append_page_hint(lines, total, page_from, len(rows))
    return _trim_markdown(lines)


def markdown_conclusion(data: Dict[str, Any], page_from: int) -> str:
    total = data.get("total", 0)
    rows = data.get("list") if isinstance(data.get("list"), list) else []
    lines = [f"## 管理层情绪结论（本页 {len(rows)} 条，接口 total={total}）", ""]
    if not rows:
        lines.append("未找到符合条件的管理层情绪结论。")
        return "\n".join(lines).strip()
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = _text(row.get("securityName"))
        code = _text(row.get("securityCode"))
        title = f"{name}（{code}）" if name and code else (name or code or "未知证券")
        lines.append(f"### {title}")
        lines.append(f"- **发布时间**：{_text(row.get('publishTime')) or '-'}")
        source_line = _source_line(row.get("source"))
        if source_line:
            lines.append(source_line)
        previous_line = _source_line(row.get("previousSource"), prefix="上一次来源")
        if previous_line:
            lines.append(previous_line)
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        source_type = _text(source.get("sourceType"))
        source_id = _text(source.get("sourceId"))
        if source_type and source_id:
            lines.append(f"- **取明细**：`--type detail --source-type {source_type} --source-id {source_id}`")
        lines.append("")
        summary = row.get("sentimentSummary") if isinstance(row.get("sentimentSummary"), dict) else {}
        lines.append("**情绪结论**")
        lines.append("")
        lines.append(f"- **总体情绪**：{_text(summary.get('overallSentiment')) or '（无）'}")
        lines.append(f"- **主要影响因素**：{_text(summary.get('questionCategorySentiment')) or '（无）'}")
        change = summary.get("qaSentimentChange")
        lines.append(f"- **重点情绪变化**：{_text(change) or '（无上一次可对比记录）'}")
        lines.append("")
        signal = row.get("sentimentSignal") if isinstance(row.get("sentimentSignal"), dict) else {}
        lines.append("**情绪信号**")
        lines.append("")
        lines.append(f"- **正面回应程度**：{_text(signal.get('responsivenessSignal')) or '（无）'}")
        lines.append(f"- **回复乐观度**：{_text(signal.get('polaritySignal')) or '（无）'}")
        lines.append(f"- **回复确定度**：{_text(signal.get('convictionSignal')) or '（无）'}")
        lines.append("")
        contrasts = row.get("qaSentimentContrast") if isinstance(row.get("qaSentimentContrast"), list) else []
        lines.append("**重点 QA 情绪对比**")
        lines.append("")
        if not contrasts:
            lines.append("本期没有可对比的上一次会议。")
            lines.append("")
        for index, item in enumerate(contrasts, 1):
            if not isinstance(item, dict):
                continue
            lines.append(f"#### {index}. {_text(item.get('headline')) or '（无标题）'}")
            lines.append("")
            lines.append(_text(item.get("detail")) or "（无说明）")
            lines.append("")
            _append_qa_block(lines, "上一次", item.get("previousQaList"))
            _append_qa_block(lines, "本次", item.get("currentQaList"))
        lines.append("---")
        lines.append("")
    _append_page_hint(lines, total, page_from, len(rows))
    return _trim_markdown(lines)


def markdown_detail(data: Dict[str, Any], source_type: str, source_id: str) -> str:
    total = data.get("total", 0)
    rows = data.get("list") if isinstance(data.get("list"), list) else []
    type_label = _SOURCE_TYPE_LABEL.get(source_type, source_type)
    lines = [f"## 管理层情绪明细（{type_label} / {source_id}，共 {total} 条）", ""]
    if not rows:
        lines.append("未找到该来源的问答情绪明细。")
        return "\n".join(lines).strip()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        brief = _text(row.get("questionBrief")) or "（无简述）"
        lines.append(f"### {index}. {brief}")
        cat_name = _text(row.get("questionCategoryName"))
        cat_code = _text(row.get("questionCategory"))
        cat = f"{cat_name}（{cat_code}）" if cat_name and cat_code else (cat_name or cat_code or "-")
        lines.append(f"- **问答 ID**：{_text(row.get('qaId')) or '-'}")
        lines.append(f"- **问题类型**：{cat}")
        lines.append("")
        lines.append("**问题**")
        lines.append("")
        lines.append(_text(row.get("question")) or "（无）")
        lines.append("")
        lines.append("**回答**")
        lines.append("")
        lines.append(_text(row.get("answer")) or "（无）")
        lines.append("")
        lines.append("| 维度 | 评分 | 判断依据 | 判断理由 |")
        lines.append("| --- | --- | --- | --- |")
        lines.append(
            "| 正面回应程度 | "
            + " | ".join(
                [
                    _md_cell(_score_with_label(row.get("qaResponsiveness"), _RESPONSIVENESS_LABEL)),
                    _md_cell(row.get("responsivenessQuote")),
                    _md_cell(row.get("responsivenessReason")),
                ]
            )
            + " |"
        )
        lines.append(
            "| 回复乐观度 | "
            + " | ".join(
                [
                    _md_cell(_score_with_label(row.get("qaPolarity"), _POLARITY_LABEL)),
                    _md_cell(row.get("polarityQuote")),
                    _md_cell(row.get("polarityReason")),
                ]
            )
            + " |"
        )
        lines.append(
            "| 回复确定度 | "
            + " | ".join(
                [
                    _md_cell(_score_with_label(row.get("qaConviction"), _CONVICTION_LABEL)),
                    _md_cell(row.get("convictionQuote")),
                    _md_cell(row.get("convictionReason")),
                ]
            )
            + " |"
        )
        lines.append("")
    return _trim_markdown(lines)


def _append_page_hint(lines: List[str], total: Any, page_from: int, shown: int) -> None:
    try:
        total_n = int(total)
    except (TypeError, ValueError):
        return
    if total_n > page_from + shown:
        lines.append(f"还有更多，可用 `--page-from {page_from + shown}` 继续。")
        lines.append("")


def _trim_markdown(lines: List[str]) -> str:
    while lines and lines[-1].strip() == "":
        lines.pop()
    while lines and lines[-1].strip() == "---":
        lines.pop()
    return "\n".join(lines).strip()


def _resolve_securities(securities: List[str]) -> Tuple[List[str], List[str], Optional[str]]:
    codes: List[str] = []
    abbrs: List[str] = []
    for token in securities:
        raw = str(token).strip()
        if not raw:
            continue
        if _CODE_PATTERN.match(raw.upper()):
            code = raw.upper()
            abbr = code
            resp = security_search_basic(raw, output_limit=1, category=["stock", "dr"])
            if resp.get("state") == "success" and resp.get("data"):
                info = resp["data"][0]
                found = _text(info.get("security_code")).upper()
                if found == code:
                    abbr = _text(info.get("security_abbr")) or code
        else:
            resp = security_search_basic(raw, output_limit=1, category=["stock", "dr"])
            if resp.get("state") != "success" or not resp.get("data"):
                message = resp.get("message") or f"证券 {raw} 不存在"
                return [], [], message
            info = resp["data"][0]
            code = _text(info.get("security_code"))
            abbr = _text(info.get("security_abbr")) or code
            if not code:
                return [], [], f"证券 {raw} 解析结果缺少代码"
        if code not in codes:
            codes.append(code)
            abbrs.append(abbr)
    return codes, abbrs, None


def _post_json(url: str, payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    headers = get_authorization_headers()
    resp = authorized_request("POST", url, headers=headers, json=payload, timeout=300)
    if resp.status_code != 200:
        return None, resp.text
    try:
        body = resp.json()
    except Exception as exc:
        return None, str(exc)
    if not isinstance(body, dict):
        return None, "响应不是 JSON 对象"
    return body, None


def _error_message(body: Dict[str, Any]) -> str:
    code = _text(body.get("code"))
    error_type = _text(body.get("errorType"))
    msg = _text(body.get("msg")) or "请求失败"
    tag = "/".join(part for part in (code, error_type) if part)
    return f"[{tag}] {msg}" if tag else msg


def _fail(message: str, output_dir: Optional[str]) -> str:
    return format_response(
        {"state": "error", "message": message, "data": [], "usage": {}},
        METHOD_NAME,
        output_dir=output_dir,
    )


def _success(
    markdown: str,
    message: str,
    usage: Dict[str, Any],
    output_dir: Optional[str],
    security_abbr: str = "",
    security_code: str = "",
    type_label: str = "",
) -> str:
    row = {
        "markdown": markdown,
        "type": type_label,
        "securityAbbr": security_abbr,
        "securityCode": security_code,
    }
    return format_response(
        {
            "state": "success",
            "message": message,
            "data": [{"data": [row], "module": "agent", "type": "management-sentiment"}],
            "usage": usage,
        },
        METHOD_NAME,
        output_dir=output_dir,
    )


def management_sentiment(
    sentiment_type: str,
    securities: Optional[List[str]] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    page_from: int = 0,
    page_size: Optional[int] = None,
    source_type: Optional[str] = None,
    source_id: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> str:
    kind = normalize_sentiment_type(sentiment_type)
    if not kind:
        valid = "、".join(f"{key}（{label}）" for key, label in _TYPE_LABEL.items())
        return _fail(f"无法识别 --type：{sentiment_type}。可选：{valid}", output_dir)
    label = _TYPE_LABEL[kind]

    if kind == "detail":
        source_token = _text(source_type) or "conference"
        normalized_source = _SOURCE_TYPE_ALIASES.get(source_token) or _SOURCE_TYPE_ALIASES.get(source_token.lower())
        if not normalized_source:
            return _fail("source_type 仅支持 conference（电话会议）", output_dir)
        source_key = _text(source_id)
        if not source_key:
            return _fail("明细查询必须提供 source_id（来自指标或结论结果里的 source.sourceId）", output_dir)
        body, err = _post_json(DETAIL_URL, {"sourceType": normalized_source, "sourceId": source_key})
        if err:
            return _fail(err, output_dir)
        if body is None:
            return _fail("空响应", output_dir)
        if str(body.get("code", "")) != "000000" or body.get("status") is not True:
            return _fail(_error_message(body), output_dir)
        data = body.get("data") if isinstance(body.get("data"), dict) else {"total": 0, "list": []}
        markdown = markdown_detail(data, normalized_source, source_key)
        message = f"{_text(body.get('msg')) or '请求成功'}\n提示：明细接口按 {POINTS_PER_DETAIL_CALL} 积分/次计费。"
        return _success(
            markdown,
            message,
            {"management-sentiment": POINTS_PER_DETAIL_CALL},
            output_dir,
            type_label=label,
        )

    try:
        start = _validate_time(start_time, "start_time", end_of_day=False)
        end = _validate_time(end_time, "end_time", end_of_day=True)
    except ValueError as exc:
        return _fail(str(exc), output_dir)
    if start and end and start > end:
        return _fail("开始时间不能晚于结束时间", output_dir)

    try:
        frm = int(page_from or 0)
    except (TypeError, ValueError):
        return _fail("page_from 须为大于等于 0 的整数", output_dir)
    if frm < 0:
        return _fail("page_from 须为大于等于 0 的整数", output_dir)
    if page_size is None:
        size = DEFAULT_PAGE_SIZE[kind]
    else:
        try:
            size = int(page_size)
        except (TypeError, ValueError):
            return _fail(f"page_size 取值范围为 1~{PAGE_SIZE_MAX}", output_dir)
    if size < 1 or size > PAGE_SIZE_MAX:
        return _fail(f"page_size 取值范围为 1~{PAGE_SIZE_MAX}", output_dir)

    tokens = _as_list(securities)
    codes: List[str] = []
    abbrs: List[str] = []
    if tokens:
        codes, abbrs, resolve_err = _resolve_securities(tokens)
        if resolve_err:
            return _fail(resolve_err, output_dir)

    payload: Dict[str, Any] = {"from": frm, "size": size}
    if start:
        payload["startTime"] = start
    if end:
        payload["endTime"] = end
    if codes:
        payload["securityList"] = codes

    url = INDICATOR_URL if kind == "indicator" else CONCLUSION_URL
    body, err = _post_json(url, payload)
    if err:
        return _fail(err, output_dir)
    if body is None:
        return _fail("空响应", output_dir)
    if str(body.get("code", "")) != "000000" or body.get("status") is not True:
        return _fail(_error_message(body), output_dir)

    data = body.get("data") if isinstance(body.get("data"), dict) else {"total": 0, "list": []}
    rows = data.get("list") if isinstance(data.get("list"), list) else []
    if kind == "indicator":
        markdown = markdown_indicator(data, frm)
    else:
        markdown = markdown_conclusion(data, frm)
    n = len(rows)
    usage = {"management-sentiment": n * POINTS_PER_RECORD} if n else {}
    tip = f"本次返回 {n} 条，按 {POINTS_PER_RECORD} 积分/条计费。" if n else "未找到记录，不计积分。"
    message = f"{_text(body.get('msg')) or '请求成功'}\n提示：{tip}"
    if codes:
        pairs = [f"{abbr}({code})" for abbr, code in zip(abbrs, codes)]
        message += "\n匹配到的证券：" + "、".join(pairs)
    return _success(
        markdown,
        message,
        usage,
        output_dir,
        security_abbr="、".join(abbrs),
        security_code="、".join(codes),
        type_label=label,
    )


def main():
    import argparse

    try:
        if not check_version():
            print("[WARNING] 存在 Gangtise agent 版本更新，请与用户确认是否更新\n")
    except Exception:
        print("[WARNING] 检查 Gangtise agent 版本失败\n")

    parser = argparse.ArgumentParser(
        description="公司管理层情绪：指标、结论、问答明细（通过 -t/--type 指定）。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-t",
        "--type",
        required=True,
        dest="sentiment_type",
        help="indicator 指标 / conclusion 结论 / detail 明细；指标与结论按证券和时间检索，明细用 source-id",
    )
    parser.add_argument("--securities", default=None, help="证券名称或代码，逗号分隔。仅 indicator / conclusion")
    parser.add_argument("-st", "--start-time", default=None, help="开始时间 yyyy-MM-dd 或 yyyy-MM-dd HH:mm:ss")
    parser.add_argument("-et", "--end-time", default=None, help="结束时间 yyyy-MM-dd 或 yyyy-MM-dd HH:mm:ss")
    parser.add_argument("--page-from", type=int, default=0, help="分页起始，从 0 开始")
    parser.add_argument("--page-size", type=int, default=None, help=f"单页条数，1~{PAGE_SIZE_MAX}；指标默认 20，结论默认 10")
    parser.add_argument("--source-type", default=None, help="明细来源类型，目前仅 conference（电话会议）")
    parser.add_argument("--source-id", default=None, help="明细来源 ID，取指标或结论结果中的 source.sourceId")
    parser.add_argument("-od", "--output-dir", default=None, help="结果保存目录路径")
    args = parser.parse_args()

    try:
        out = management_sentiment(
            sentiment_type=args.sentiment_type,
            securities=_as_list(args.securities) or None,
            start_time=args.start_time,
            end_time=args.end_time,
            page_from=args.page_from,
            page_size=args.page_size,
            source_type=args.source_type,
            source_id=args.source_id,
            output_dir=args.output_dir,
        )
    except ValidationError as exc:
        print(str(exc))
        sys.exit(getattr(exc, "exit_code", 1) or 1)
    print(out)


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
