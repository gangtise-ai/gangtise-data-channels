if __name__ == "__main__" and not __package__:
    import importlib.util
    from pathlib import Path as _P
    _launch = _P(__file__).resolve().parent / "_launch.py"
    _spec = importlib.util.spec_from_file_location("_gts_skill_launch", _launch)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(_mod)
    raise SystemExit(_mod.relaunch(__file__))

import os
import re
import uuid
from typing import Dict, List, Any, Optional
# import logging
# from logging.handlers import TimedRotatingFileHandler
import pandas as pd
import datetime
import json
import requests

# 通过 ak/sk 获取 临时 authorization

from .gts_auth import (
    append_consumed_points_to_saved_file,
    apply_consumed_points,
    authorized_request,
    get_authorization_headers,
    get_authorization_token,
    get_headers_extra,
    gangtise_domain,
    invalidate_authorization,
)
from .gts_runtime import failure_result, success_result
from .gts_runtime import to_timestamp13

def __getattr__(name):
    if name == "GTS_AUTHORIZATION":
        return get_authorization_token()
    if name == "HEADERS_EXTRA":
        return get_headers_extra()
    raise AttributeError(name)

DEPLOY_ENV = os.getenv("DEPLOY_ENV", "local")
GTS_ACCESS_KEY = os.getenv("GTS_ACCESS_KEY", None)
GTS_SECRET_KEY = os.getenv("GTS_SECRET_KEY", None)
GTS_AUTHORIZATION_PATH = os.getenv(
    "GTS_AUTHORIZATION_PATH",
    os.path.join(os.path.abspath(os.path.dirname(__file__)), ".authorization"),
)
    
def _env_truthy(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")

GTS_SAVE_FILE = _env_truthy("GTS_SAVE_FILE", False)
GTS_SAVE_EXTENSION = os.getenv("GTS_SAVE_EXTENSION", "md")

GANGTISE_DATA_DOMAIN = gangtise_domain("GANGTISE_DATA_DOMAIN", "https://openapi.gangtise.com/application/open-data")
GANGTISE_INSIGHT_DOMAIN = gangtise_domain("GANGTISE_INSIGHT_DOMAIN", "https://openapi.gangtise.com/application/open-insight")
RAG_URL = GANGTISE_DATA_DOMAIN + "/ai/search/knowledge_base"
FILE_URL = GANGTISE_DATA_DOMAIN + "/ai/resource/download"
SUMMARY_DOWNLOAD_URL = GANGTISE_INSIGHT_DOMAIN + "/summary/v2/download/file"
COMPANY_ANNOUNCEMENT_DOWNLOAD_URL = GANGTISE_INSIGHT_DOMAIN + "/announcement/download/file"
HK_ANNOUNCEMENT_DOWNLOAD_URL = GANGTISE_INSIGHT_DOMAIN + "/announcement-hk/download/file"
REPORT_DOWNLOAD_URL = GANGTISE_INSIGHT_DOMAIN + "/broker-report/download/file"
FOREIGN_REPORT_DOWNLOAD_URL = GANGTISE_INSIGHT_DOMAIN + "/foreign-report/download/file"
WORK_PATH = os.getenv("WORK_PATH", None)
if WORK_PATH:
    gangtise_workspace_path = WORK_PATH
elif DEPLOY_ENV == "local":
    def _find_openclaw_root():
        """向上遍历目录直到找到 .openclaw，返回其上级目录作为执行目录"""
        path = os.path.abspath(os.path.dirname(__file__))
        openclaw_dir_got = False
        while path != os.path.dirname(path):
            dir_name = os.path.basename(path)
            if dir_name in (".openclaw"):
                openclaw_dir_got = True
                return os.path.abspath(path)
            path = os.path.dirname(path)
        path = os.path.abspath(os.path.dirname(__file__))
        if not openclaw_dir_got:
            openclaw_dir_got = False
            while path != os.path.dirname(path):
                dir_name = os.path.basename(path)
                if dir_name in (".agent"):
                    openclaw_dir_got = True
                    return os.path.abspath(path)
                path = os.path.dirname(path)
        path = os.path.abspath(os.path.dirname(__file__))
        if not openclaw_dir_got:
            openclaw_dir_got = False
            while path != os.path.dirname(path):
                dir_name = os.path.basename(path)
                if dir_name in ("workspace"):
                    openclaw_dir_got = True
                    return os.path.abspath(path)
                path = os.path.dirname(path)
        path = os.path.abspath(os.path.dirname(__file__))
        if not openclaw_dir_got:
            openclaw_dir_got = False
            while path != os.path.dirname(path):
                dir_name = os.path.basename(path)
                if dir_name in ("skills"):
                    openclaw_dir_got = True
                    return os.path.abspath(os.path.dirname(path))
                path = os.path.dirname(path)
        return os.path.abspath(os.getcwd())

    openclaw_root = _find_openclaw_root()
    if openclaw_root.endswith("workspace"):
        gangtise_workspace_path = os.path.join(openclaw_root, "gangtise")
    else:
        gangtise_workspace_path = os.path.join(openclaw_root, "workspace", "gangtise")
else:
    gangtise_workspace_path = "/opt/data/workspace/default"

def _ensure_dir(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass

usage_dir = os.path.join(gangtise_workspace_path, ".usage")
file_dir = os.path.join(gangtise_workspace_path, "files")

FILE_TYPE_MAP = {
    "研究报告": 10,
    "外资研报": 11,
    "内部报告": 20,
    "AI云盘": 30,
    "首席观点": 40,
    "公司公告": 50,
    "港股公告": 51,
    "会议纪要": 60,
    "调研纪要": 70,
    "网络纪要": 80,
    "产业公众号": 90,
}

FILE_TYPE_MAP_REVERSE = {
    v: k for k, v in FILE_TYPE_MAP.items()
}

def data_to_md(data: pd.DataFrame, range: List[int]=None, max_cell_length: int=None):
    data_copy = data.copy()
    if "metadata" in data_copy.columns:
        data_copy = data_copy.drop(columns=["metadata"])
    content = "| " + " | ".join(data_copy.columns) + " |\n"
    content += "| " + " | ".join(["-" for _ in data_copy.columns]) + " |\n"
    omitted = False
    for i, row in enumerate(data_copy.to_dict(orient="records")):
        if range:
            if i in range:
                if max_cell_length:
                    content += "| " + " | ".join([re.sub(r"\s+", " ", str(row[key]).replace("\n"," ")).replace("|", "")[:max_cell_length]+"..." if len(re.sub(r"\s+", " ", str(row[key])).replace("|", "")) > max_cell_length else re.sub(r"\s+", " ", str(row[key])).replace("|", "") for key in row.keys()]) + " |\n"
                else:
                    content += "| " + " | ".join([re.sub(r"\s+", " ", str(row[key]).replace("\n"," ")).replace("|", "") for key in row.keys()]) + " |\n"
            elif not omitted:
                content += "| ... |\n"
                omitted = True
        else:
            if max_cell_length:
                content += "| " + " | ".join([re.sub(r"\s+", " ", str(row[key]).replace("\n"," ")).replace("|", "")[:max_cell_length]+"..." if len(re.sub(r"\s+", " ", str(row[key])).replace("|", "")) > max_cell_length else re.sub(r"\s+", " ", str(row[key])).replace("|", "") for key in row.keys()]) + " |\n"
            else:
                content += "| " + " | ".join([re.sub(r"\s+", " ", str(row[key]).replace("\n"," ")).replace("|", "") for key in row.keys()]) + " |\n"
    content = content[:-1]
    return content.strip()

def add_usages(usages_list: List[Dict[str, Any]]):
    usages = {}
    for usages_item in usages_list:
        if len(usages_item) == 0:
            continue
        for k,v in usages_item.items():
            if k not in usages:
                usages[k] = v
            else:
                usages[k] = usages[k] + v
    return usages

def format_file_time(value: Any) -> str:
    """将文件时间转为 yyyy-MM-dd HH:MM:SS；支持秒/毫秒时间戳，已是字符串则原样返回。"""
    if value is None:
        return ""
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return ""
        if re.fullmatch(r"\d{10,13}", s):
            ts = int(s)
        else:
            return s
    elif isinstance(value, (int, float)):
        ts = int(value)
    else:
        return str(value).strip()

    if ts > 10_000_000_000:
        ts //= 1000
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError, OverflowError):
        return str(value)

def _normalize_kb_file_records(data: List[Dict[str, Any]]) -> None:
    for file in data:
        if "文件时间" in file:
            file["文件时间"] = format_file_time(file.get("文件时间"))

def _json_records_with_skill(data, skill: str):
    """JSON 落盘时给每条记录带上 skill，供溯源区分打开逻辑（不改原列表）。"""
    if not isinstance(data, list):
        return data
    stamped = []
    for item in data:
        if isinstance(item, dict):
            row = dict(item)
            row["skill"] = skill
            stamped.append(row)
        else:
            stamped.append(item)
    return stamped

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

def format_response(response: dict, method_name: str, output_dir: Optional[str] = None, additional_message: str = ""):
    should_save = bool(output_dir) or GTS_SAVE_FILE
    points_note = apply_consumed_points(response)

    # 保存usage（含本次 Consumed-Point 汇总）
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    now = datetime.datetime.now().strftime("%H%M%S")
    usage_path = os.path.join(usage_dir, f"{today}.json")
    if should_save and response.get("usage", None):
        _ensure_dir(usage_dir)
        if os.path.exists(usage_path):
            with open(usage_path, "r", encoding="utf-8") as f:
                usage = json.load(f)
            if now in usage:
                now_usage = add_usages([response["usage"], usage[now]])
            else:
                now_usage = response["usage"]
            usage.update({now: now_usage})
        else:
            usage = {now: response["usage"]}
        with open(usage_path, "w", encoding="utf-8") as f:
            json.dump(usage, f, ensure_ascii=False)

    # 保存结果
    return_message = ""
    method_name_map = {
        "block_component": "板块成分信息",
        "financial": "财务数据",
        "industry_indicator": "行业指标数据",
        "main_business": "主营业务数据",
        "quote": "行情数据",
        "security": "证券信息",
        "shareholder": "股东数据",
        "valuation": "估值数据",
        "rag": "知识库检索",
    }
    if response["state"] == "success":
        for item in response["data"]:
            module_name = item["module"]
            data = item["data"]
            _normalize_kb_file_records(data)
            if should_save:
                extension = GTS_SAVE_EXTENSION
                if output_dir:
                    process_dir = output_dir
                else:
                    process_dir = os.path.join(gangtise_workspace_path, method_name)
                try:
                    process_path = _unique_result_path(process_dir, module_name, extension)
                except RuntimeError as exc:
                    return f"错误信息：{exc}"
                if GTS_SAVE_EXTENSION == "md":
                    with open(process_path, "w", encoding="utf-8") as f:
                        for i, file in enumerate(data):
                            f.write(f"### 查询结果 {i+1}\n\n")
                            f.write(f"标题：{file['标题']}\n")
                            f.write(f"文件时间：{file['文件时间']}\n")
                            f.write(f"内容：\"\"\"\n{file['摘要']}\n\"\"\"\n")
                            f.write(f"file-type：{file['类型']}\n")
                            f.write(f"file-id：{file['类型ID']}")
                            if i < len(data) - 1:
                                f.write("\n\n---\n\n")
                    append_consumed_points_to_saved_file(process_path, points_note)
                elif GTS_SAVE_EXTENSION == "json":
                    with open(process_path, "w", encoding="utf-8") as f:
                        json.dump(
                            _json_records_with_skill(data, "gangtise-kb"),
                            f,
                            ensure_ascii=False,
                        )
                # 落盘时正文最多展示 5 个 chunk 作为示例，完整结果见文件
                preview_n = 5
                preview_chunks = data[:preview_n]
                sample_data = ""
                for file in preview_chunks:
                    sample_data += f"标题：{file['标题']}\n"
                    sample_data += f"文件时间：{file['文件时间']}\n"
                    sample_data += f"内容：\"\"\"\n{file['摘要']}\n\"\"\"\n"
                    sample_data += f"file-type：{file['类型']}\n"
                    sample_data += f"file-id：{file['类型ID']}"
                    sample_data += "\n\n---\n\n"
                total = len(data)
                if total > preview_n:
                    count_line = f"仅展示前 {preview_n} 条示例，共 {total} 条；完整结果见文件"
                else:
                    count_line = f"查询结果共计{total}条"
                return_message += (
                    "### "
                    + method_name_map[method_name]
                    + " 查询结果:\n\n---\n\n"
                    + sample_data
                    + count_line
                    + f"\n\n<!-- 所有查询结果已保存到{GTS_SAVE_EXTENSION}：`"
                    + os.path.abspath(process_path)
                    + "` -->"
                )
            else:
                sample_data = ""
                for i, file in enumerate(data):
                    sample_data += f"标题：{file['标题']}\n"
                    sample_data += f"文件时间：{file['文件时间']}\n"
                    if file.get("摘要", None):
                        sample_data += f"摘要：\"\"\"\n{file['摘要']}\n\"\"\"\n"
                    sample_data += f"file-type：{file['类型']}\n"
                    sample_data += f"file-id：{file['类型ID']}"
                    sample_data += "\n\n---\n\n"
                return_message += "### " + method_name_map[method_name] + "查询结果:\n\n---\n\n" + sample_data
                return_message += f"查询结果共计{len(data)}条"
    else:
        return failure_result(response)
    if additional_message:
        return_message += "\n" + additional_message
    return success_result(return_message, response)

def load_securities_from_file(path: str) -> List[str]:
    full_path = path
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"证券文件不存在: {path}")
    df = pd.read_csv(full_path)
    if "security_abbr" in df.columns:
        return [str(x) for x in df["security_abbr"].dropna().tolist()]
    if "security_code" in df.columns:
        return [str(x) for x in df["security_code"].dropna().tolist()]
    raise ValueError("证券文件必须包含 security_code 或 security_abbr 列")

if __name__ == "__main__":
    print("检查 gangtise-kb 相关配置")
    if not get_authorization_token():
        print("  无法检测到gangtise密钥环境变量或授权文件, gangtise-kb 无法正常工作")
    else:
        print("  检测到gangtise授权文件, gangtise-kb 可以正常工作")
    if GTS_SAVE_FILE:
        print("  环境变量 GTS_SAVE_FILE 为 True, gangtise服务端 将保存查询结果到文件中")
    else:
        print("  环境变量 GTS_SAVE_FILE 为 False（未配置或非真值）, gangtise服务端 将不保存查询结果到文件中")
    print(f"  gangtise-kb 工作文件目录: {gangtise_workspace_path}")

_TRUE_WORDS = {"1", "true", "yes", "y", "on", "是"}
_FALSE_WORDS = {"0", "false", "no", "n", "off", "否"}

def parse_bool_flag(value) -> bool:
    """argparse 布尔开关：`-d` 视为 true，也接受 `-d true/false`。"""
    text = str(value).strip().lower()
    if text in _TRUE_WORDS:
        return True
    if text in _FALSE_WORDS:
        return False
    import argparse

    raise argparse.ArgumentTypeError(f"无效布尔值: {value}（可用 true / false）")
