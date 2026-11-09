# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-private/scripts/utils.py
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

import os
import re
from typing import Dict, List, Any, Optional, Tuple
import hashlib
import pandas as pd
import datetime
import uuid
import requests
import json

FILE_DEFAULT_LIMIT = {
    "wechat_message": 1000,
    "private_meeting": 100,
    "private_record": 100,
    "private_cloud": 100,
}

from gangtise_core.auth import (
    authorized_request,
    get_authorization_headers,
    get_authorization_token,
    get_headers_extra,
    gangtise_domain,
    invalidate_authorization,
)
from gangtise_core.skill_runtime import failure_result, success_result

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

GANGTISE_VAULT_DOMAIN = gangtise_domain("GANGTISE_VAULT_DOMAIN", "https://openapi.gangtise.com/application/open-vault")
WECHAT_GROUP_MSG_LIST_URL = GANGTISE_VAULT_DOMAIN + "/wechatgroupmsg/list"
WECHAT_GROUP_CHATROOM_URL = GANGTISE_VAULT_DOMAIN + "/wechatgroupmsg/chatroomId"
GET_POOL_LIST_URL = GANGTISE_VAULT_DOMAIN + "/stock-pool/getPoolList"
GET_STOCK_LIST_URL = GANGTISE_VAULT_DOMAIN + "/stock-pool/getStockList"
CREATE_POOL_URL = GANGTISE_VAULT_DOMAIN + "/stock-pool/createPool"
UPDATE_POOL_URL = GANGTISE_VAULT_DOMAIN + "/stock-pool/updatePool"
DELETE_POOL_URL = GANGTISE_VAULT_DOMAIN + "/stock-pool/deletePool"
ADD_STOCK_URL = GANGTISE_VAULT_DOMAIN + "/stock-pool/addStock"
DELETE_STOCK_URL = GANGTISE_VAULT_DOMAIN + "/stock-pool/deleteStock"
GET_NOTE_LIST_URL = GANGTISE_VAULT_DOMAIN + "/stock-pool/getNoteList"
ADD_NOTE_URL = GANGTISE_VAULT_DOMAIN + "/stock-pool/addNote"
UPDATE_NOTE_URL = GANGTISE_VAULT_DOMAIN + "/stock-pool/updateNote"
DELETE_NOTE_URL = GANGTISE_VAULT_DOMAIN + "/stock-pool/deleteNote"
MY_CONFERENCE_LIST_URL = GANGTISE_VAULT_DOMAIN + "/my-conference/getList"
MY_CONFERENCE_DOWNLOAD_URL = GANGTISE_VAULT_DOMAIN + "/my-conference/download/file"
RECORD_LIST_URL = GANGTISE_VAULT_DOMAIN + "/record/getList"
RECORD_DOWNLOAD_URL = GANGTISE_VAULT_DOMAIN + "/record/download/file"
DRIVE_LIST_URL = GANGTISE_VAULT_DOMAIN + "/drive/getList"
DRIVE_DOWNLOAD_URL = GANGTISE_VAULT_DOMAIN + "/drive/download/file"
DRIVE_FOLDER_LIST_URL = GANGTISE_VAULT_DOMAIN + "/drive/getFolderList"
DRIVE_UPLOAD_URL = GANGTISE_VAULT_DOMAIN + "/drive/uploadFile"
DRIVE_CREATE_FOLDER_URL = GANGTISE_VAULT_DOMAIN + "/drive/createFolder"
DRIVE_DELETE_FILE_URL = GANGTISE_VAULT_DOMAIN + "/drive/deleteFile"
DRIVE_DELETE_FOLDER_URL = GANGTISE_VAULT_DOMAIN + "/drive/deleteFolder"
DRIVE_MOVE_FILE_URL = GANGTISE_VAULT_DOMAIN + "/drive/moveFile"
DRIVE_MOVE_FOLDER_URL = GANGTISE_VAULT_DOMAIN + "/drive/moveFolder"
DRIVE_RENAME_URL = GANGTISE_VAULT_DOMAIN + "/drive/rename"
DRIVE_COPY_URL = GANGTISE_VAULT_DOMAIN + "/drive/copy"
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

def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

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

_FILE_SKIP_IN_BODY = frozenset({"标题", "文件时间", "消息时间", "文件内容", "类型", "类型ID", "中文标题"})
_FILE_MULTILINE = frozenset({"摘要", "中文摘要", "正文", "消息全文"})

def _save_file_enabled() -> bool:
    return bool(GTS_SAVE_FILE)

def _format_file_record_text(file: dict, method_name: str, module_name: str, output_dir: Optional[str] = None) -> str:
    lines: List[str] = []
    if file.get("标题"):
        lines.append(f"标题：{file['标题']}")
    if file.get("中文标题"):
        lines.append(f"中文标题：{file['中文标题']}")
    if file.get("消息时间"):
        lines.append(f"消息时间：{file['消息时间']}")
    if file.get("文件内容"):
        if file.get("文件内容", {}).get("status", "failed") == "success":
            file_path = _alloc_workspace_path(
                method_name, module_name, GTS_SAVE_EXTENSION, output_dir,
                filename=file.get("文件内容", {}).get("filename", None),
            )
            if file_path[0] and file_path[1] == "exist":
                existed_file_sha = hashlib.sha256(open(file_path[0], "rb").read()).hexdigest()
                response_content_sha = hashlib.sha256(file.get("文件内容").get("file_bytes")).hexdigest()
                if existed_file_sha == response_content_sha:
                    lines.append(f"文件已存在：`{os.path.abspath(file_path[0])}`")
                else:
                    iteration = 1
                    base_path = file_path[0]
                    name, ext = os.path.splitext(os.path.basename(base_path))
                    dirname = os.path.dirname(base_path)
                    new_path = base_path
                    while os.path.exists(new_path):
                        new_path = os.path.join(dirname, f"{name}({iteration}){ext}")
                        iteration += 1
                    with open(new_path, "wb") as f:
                        f.write(file.get("文件内容").get("file_bytes"))
                    lines.append(f"文件名重复，已自动重命名并下载到 `{os.path.abspath(new_path)}`")
            elif file_path[0]:
                with open(file_path[0], "wb") as f:
                    f.write(file.get("文件内容").get("file_bytes"))
                lines.append(f"文件已下载到 `{os.path.abspath(file_path[0])}`")
            else:
                lines.append(f"文件下载失败：{file_path[1]}")
        else:
            lines.append(f"文件下载失败：{file.get('文件内容').get('message')}")
    for key, value in file.items():
        if key in _FILE_SKIP_IN_BODY or not value:
            continue
        if key in _FILE_MULTILINE:
            lines.append(f"{key}：\"\"\"\n{value}\n\"\"\"")
        else:
            lines.append(f"{key}：{value}")
    if file.get("类型"):
        lines.append(f"file-type：{file['类型']}")
    if file.get("类型ID") is not None and str(file.get("类型ID", "")).strip() != "":
        lines.append(f"file-id：{file['类型ID']}")
    return "\n".join(lines)

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


def _alloc_workspace_path(
    method_name: str,
    module_name: str,
    extension: str,
    output_dir: Optional[str] = None,
    filename: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    if output_dir:
        process_dir = output_dir
    else:
        process_dir = os.path.join(gangtise_workspace_path, method_name)
    os.makedirs(process_dir, exist_ok=True)
    if filename:
        process_path = os.path.join(process_dir, filename)
        if os.path.exists(process_path):
            return process_path, "exist"
        return process_path, None
    try:
        return _unique_result_path(process_dir, module_name, extension), None
    except RuntimeError as exc:
        return None, f"错误信息：{exc}"

def format_response(
    response: dict,
    method_name: str,
    output_dir: Optional[str] = None,
    additional_message: str = "",
):
    should_save = bool(output_dir) or GTS_SAVE_FILE
    # 保存 usage
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

    return_message = response.get("message", "") + "\n\n" if response.get("message", "") else ""
    method_name_map = {
        "stockpool": "股票池",
        "wechat_message": "微信群消息",
        "private_meeting": "我的会议",
        "private_record": "录音速记",
        "private_cloud": "AI云盘",
    }
    module_name_map = {
        "stockpool_pools": "股票池列表",
        "stockpool_stocks": "证券明细",
        "stockpool_notes": "个股笔记",
        "wechat_chatroom": "微信群列表",
        "wechat_message": "群消息",
        "private_meeting_list": "会议列表",
        "private_meeting_content": "会议内容",
        "private_record_list": "录音列表",
        "private_record_content": "录音内容",
        "private_cloud_list": "云盘文件列表",
        "private_cloud_content": "云盘文件内容",
        "private_cloud_folders": "子文件夹列表",
        "private_cloud_folder_files": "文件夹内文件列表",
    }

    if response["state"] == "success":
        for item in response["data"]:
            module_name = item["module"]
            data = item["data"]
            item_type = item.get("type", "files")
            label = method_name_map.get(method_name, method_name)
            sub = module_name_map.get(module_name, module_name)

            if item_type == "data":
                process_path, err = _alloc_workspace_path(method_name, module_name, "csv", output_dir)
                if err:
                    return err
                df = pd.DataFrame(data)
                df.to_csv(process_path, index=False)
                n = len(df)
                if n <= 6:
                    sample_range = list(range(n))
                else:
                    sample_range = [0, 1, 2, n - 3, n - 2, n - 1]
                sample_data = data_to_md(df, range=sample_range)
                return_message += (
                    f"### {label} · {sub}\n\n#### 样例数据:\n{sample_data}\n\n共 {n} 条\n\n"
                    f"已保存到 csv：\n`"
                    + os.path.abspath(process_path)
                    + "`\n\n---\n\n"
                )
                continue

            # type == "files"：群消息等，对齐 gangtise-file 的落盘与内联展示
            if _save_file_enabled():
                process_path, err = _alloc_workspace_path(
                    method_name, module_name, GTS_SAVE_EXTENSION, output_dir
                )
                if err:
                    return err
                if GTS_SAVE_EXTENSION == "md":
                    with open(process_path, "w", encoding="utf-8") as f:
                        for i, file in enumerate(data):
                            f.write(_format_file_record_text(file, method_name, module_name, output_dir))
                            if i < len(data) - 1:
                                f.write("\n\n---\n\n")
                elif GTS_SAVE_EXTENSION == "json":
                    with open(process_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False)
                else:
                    with open(process_path, "w", encoding="utf-8") as f:
                        for i, file in enumerate(data):
                            f.write(_format_file_record_text(file, method_name, module_name, output_dir))
                            if i < len(data) - 1:
                                f.write("\n\n---\n\n")
                # 落盘时正文最多展示 5 个 file 作为示例，完整结果见文件
                preview_n = 5
                preview = data[:preview_n]
                sample_blocks = [
                    _format_file_record_text(file, method_name, module_name, output_dir)
                    for file in preview
                ]
                sample_data = "\n\n---\n\n".join(sample_blocks)
                total = len(data)
                count_line = (
                    f"仅展示前 {preview_n} 条示例，共 {total} 条；完整结果见文件"
                    if total > preview_n
                    else f"查询结果共计 {total} 条"
                )
                return_message += (
                    f"### {label} 查询结果:\n\n---\n\n{sample_data}\n\n"
                    f"{count_line}\n\n"
                    f"<!-- 所有查询结果已保存到 {GTS_SAVE_EXTENSION}：`"
                    + os.path.abspath(process_path)
                    + "` -->\n\n---\n\n"
                )
            else:
                sample_blocks = [
                    _format_file_record_text(file, method_name, module_name, output_dir)
                    for file in data
                ]
                sample_data = "\n\n---\n\n".join(sample_blocks)
                return_message += (
                    f"### {label} 查询结果:\n\n---\n\n{sample_data}\n\n"
                    f"查询结果共计 {len(data)} 条\n\n---\n\n"
                )
    else:
        return failure_result(response)

    if additional_message:
        return_message += "\n" + additional_message
    if return_message.endswith("---\n\n"):
        return_message = return_message[:-6].strip()
    return success_result(return_message, response)

def is_code_arg(raw: str) -> bool:
    """整段参数仅含字母、数字与逗号时视为 ID/编码，否则走 search。"""
    s = (raw or "").strip()
    return bool(s) and re.fullmatch(r"[a-zA-Z,，0-9]+", s) is not None

def load_pool_ids_from_file(path: str) -> List[str]:
    full_path = path
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"股票池文件不存在: {path}")
    df = pd.read_csv(full_path)
    for col in ("pool_id", "poolId", "poolIdList"):
        if col in df.columns:
            return [str(x).strip() for x in df[col].dropna().tolist() if str(x).strip()]
    raise ValueError("股票池文件须包含 pool_id 或 poolId 列")

def load_securities_from_file(path: str) -> List[str]:
    full_path = path
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"证券文件不存在: {path}")
    df = pd.read_csv(full_path)
    if "security_abbr" in df.columns:
        return [str(x) for x in df["security_abbr"].dropna().tolist()]
    if "security_code" in df.columns:
        return [str(x) for x in df["security_code"].dropna().tolist()]
    raise ValueError("证券文件必须包含 security_abbr 或 security_code 列")

def match_best(item: str, candidates, threshold: float = 0.6):
    """
    candidates: List[str] 时返回匹配的字符串，Dict[str, Any] 时返回匹配 key 的 {k: v}。
    无匹配返回 None。
    """
    from difflib import SequenceMatcher

    if not item or not candidates:
        return None
    if item in candidates:
        return item

    is_dict = isinstance(candidates, dict)
    keys = list(candidates.keys()) if is_dict else candidates

    if item in keys:
        return {item: candidates[item]} if is_dict else item

    best_score = 0.0
    best_key = None

    for key in keys:
        if item in key or key in item:
            overlap = min(len(item), len(key))
            score = overlap / max(len(item), len(key))
            score = max(score, 0.8)
        else:
            score = SequenceMatcher(None, item, key).ratio()

        if score > best_score:
            best_score = score
            best_key = key

    if best_score >= threshold and best_key is not None:
        return {best_key: candidates[best_key]} if is_dict else best_key
    return None

PRIVATE_SKILL_VERSION = "1.0.0"
OPENAPI_SKILL_VERSION = "1.7.0"
SKILL_CHECK_URL = "https://openapi.gangtise.com/application/skills-backend/version?skill=openapi"

def check_version(large_version: bool = True):
    response = requests.get(SKILL_CHECK_URL)
    if response.status_code == 200 and large_version:
        return response.json()["state"] == "success" and response.json()["version"].split(".")[0] == OPENAPI_SKILL_VERSION.split(".")[0] and response.json()["version"].split(".")[1] == OPENAPI_SKILL_VERSION.split(".")[1]
    elif response.status_code == 200 and not large_version:
        return response.json()["state"] == "success" and response.json()["version"] == OPENAPI_SKILL_VERSION
    else:
        return False

if __name__ == "__main__":
    print("检查 gangtise-private 相关配置")
    if not get_authorization_token():
        print("  无法检测到 gangtise 密钥环境变量或授权文件，gangtise-private 无法正常工作")
    else:
        print("  已检测到 gangtise 授权，gangtise-private 可以正常工作")
    if _save_file_enabled():
        print(f"  GTS_SAVE_FILE 已启用，群消息等将保存为 {GTS_SAVE_EXTENSION}（股票池 CSV 始终落盘）")
    else:
        print("  GTS_SAVE_FILE 未启用：群消息仅在回复中展示；设置 GTS_SAVE_FILE=True 可落盘 md/json")
    if check_version(large_version=False):
        print("  gangtise-private 依赖的 OpenAPI skills 版本检查通过")
    else:
        print("  建议检查 OpenAPI skills 版本更新")
    print(f"  工作目录: {gangtise_workspace_path}")