# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-screener/scripts/utils.py
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
import sys
import json
import datetime
import uuid
from typing import Dict, List, Any, NoReturn, Optional
import requests
from gangtise_core.auth import (
    append_consumed_points_note,
    apply_consumed_points,
    authorized_request,
    get_authorization_headers,
    get_authorization_token,
    get_headers_extra,
    gangtise_domain,
    invalidate_authorization,
)

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
GTS_SAVE_EXTENSION = os.getenv("GTS_SAVE_EXTENSION", "json")

GANGTISE_INDICATOR_DOMAIN = gangtise_domain("GANGTISE_INDICATOR_DOMAIN", "https://openapi.gangtise.com/application/open-indicator")
GANGTISE_REFERENCE_DOMAIN = os.getenv(
    "GANGTISE_REFERENCE_DOMAIN",
    "https://openapi.gangtise.com/application/open-reference",
).rstrip("/")
GANGTISE_QUOTE_DOMAIN = os.getenv(
    "GANGTISE_QUOTE_DOMAIN",
    "https://openapi.gangtise.com/application/open-quote",
).rstrip("/")
INDICATOR_URL = os.getenv("INDICATOR_URL", f'{GANGTISE_INDICATOR_DOMAIN}/EDE/search')  # 查询指标及指标参数URL
INDICATOR_STOCK_URL = os.getenv("INDICATOR_STOCK_URL", f'{GANGTISE_INDICATOR_DOMAIN}/screener')  # 指标选股URL
SECTOR_SEARCH_URL = os.getenv("SECTOR_SEARCH_URL", f"{GANGTISE_REFERENCE_DOMAIN}/sectors/search")
SECURITIES_SEARCH_URL = os.getenv(
    "SECURITIES_SEARCH_URL", f"{GANGTISE_REFERENCE_DOMAIN}/securities/search"
)
QUOTE_URL = os.getenv("QUOTE_URL", f"{GANGTISE_QUOTE_DOMAIN}/kline/daily")
HTTP_TIMEOUT = 600

def die(message: str, code: int = 1) -> NoReturn:
    """Print error message and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(code)

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

def add_usages(usages_list: List[Dict[str, Any]]):
    usages = {}
    for usages_item in usages_list:
        if len(usages_item) == 0:
            continue
        for k, v in usages_item.items():
            if k not in usages:
                usages[k] = v
            else:
                usages[k] = usages[k] + v
    return usages

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


def save_data_csv(
    records: List[Dict[str, Any]],
    method_name: str = "screener",
    module_name: str = "screener",
    output_dir: Optional[str] = None,
) -> str:
    """将结果落盘为 CSV（对齐 gangtise-data format_response 的 data 路径），返回绝对路径。"""
    import csv

    if not records:
        raise ValueError("records 不能为空")

    if output_dir:
        process_dir = output_dir
    else:
        process_dir = os.path.join(gangtise_workspace_path, method_name)
    process_path = _unique_result_path(process_dir, module_name, "csv")

    # 稳定列序：先按首行键，后续行多出的键追加在末尾
    fieldnames: List[str] = list(records[0].keys())
    for rec in records[1:]:
        for k in rec.keys():
            if k not in fieldnames:
                fieldnames.append(k)

    with open(process_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow({k: rec.get(k, "") for k in fieldnames})

    return os.path.abspath(process_path)

def format_response(
    resp_text: str,
    method_name: str,
    module_name: str,
    usage: dict = None,
    output_dir: Optional[str] = None,
) -> str:
    # 合并本次 HTTP Consumed-Point 到 usage，并追加到最终回复
    carrier = {"usage": dict(usage or {})}
    points_note = apply_consumed_points(carrier)
    usage = dict(carrier.get("usage") or {})
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    now = datetime.datetime.now().strftime("%H%M%S")
    usage_path = os.path.join(usage_dir, f"{today}.json")
    if usage:
        if os.path.exists(usage_path):
            with open(usage_path, "r", encoding="utf-8") as f:
                _usage = json.load(f)
            if now in _usage:
                now_usage = add_usages([usage, _usage[now]])
            else:
                now_usage = usage
            _usage.update({now: now_usage})
        else:
            _usage = {now: usage}
        with open(usage_path, "w", encoding="utf-8") as f:
            json.dump(_usage, f, ensure_ascii=False)

    # 保存结果
    if GTS_SAVE_FILE:
        if output_dir:
            process_dir = output_dir
        else:
            process_dir = os.path.join(gangtise_workspace_path, method_name)
        os.makedirs(process_dir, exist_ok=True)
        extension = 'json'
        process_path = os.path.join(process_dir, f"{module_name}_{today}_{now}.{extension}")
        with open(process_path, "w", encoding="utf-8") as f:
            f.write(resp_text)
        # json 结构不改；积分记在 .usage，并在回复中展示
        resp_text += f"\n\n工具调用结果已保存到文件：\n`{os.path.abspath(process_path)}`\n\n"

    return append_consumed_points_note(resp_text, points_note)

OPENAPI_SKILL_VERSION = "1.7.0"
SKILL_CHECK_URL = "https://openapi.gangtise.com/application/skills-backend/version?skill=openapi"

def check_version(large_version: bool = True):
    response = requests.get(SKILL_CHECK_URL)
    if response.status_code == 200 and large_version:
        return response.json()["state"] == "success" and response.json()["version"].split(".")[0] == \
            OPENAPI_SKILL_VERSION.split(".")[0] and response.json()["version"].split(".")[1] == \
            OPENAPI_SKILL_VERSION.split(".")[1]
    elif response.status_code == 200 and not large_version:
        return response.json()["state"] == "success" and response.json()["version"] == OPENAPI_SKILL_VERSION
    else:
        return False

if __name__ == "__main__":
    print("检查 gangtise-file 相关配置")
    if not get_authorization_token():
        print("  无法检测到gangtise密钥环境变量或授权文件, gangtise-agent 无法正常工作")
    else:
        print("  检测到gangtise授权文件, gangtise-agent 可以正常工作")
    if GTS_SAVE_FILE:
        print("  环境变量 GTS_SAVE_FILE 为 True, gangtise服务端 将保存查询结果到文件中")
    else:
        print("  环境变量 GTS_SAVE_FILE 为 False（未配置或非真值）, gangtise服务端 将不保存查询结果到文件中")
    if check_version(large_version=False):
        print("  gangtise-file 版本为最新")
    else:
        print("  gangtise-file 版本不是最新, 建议进行更新")
    print(f"  gangtise-file 工作文件目录: {gangtise_workspace_path}")