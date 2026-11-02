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
import datetime
import json
from typing import Any, Dict, Optional, Tuple

import requests


from .gts_auth import (
    authorized_request,
    get_authorization_headers,
    get_authorization_token,
    get_headers_extra,
    gangtise_domain,
)
from .gts_runtime import failure_result, success_result


def __getattr__(name):
    if name == "GTS_AUTHORIZATION":
        return get_authorization_token()
    if name == "HEADERS_EXTRA":
        return get_headers_extra()
    raise AttributeError(name)


DEPLOY_ENV = os.getenv("DEPLOY_ENV", "local")

GANGTISE_TOOL_DOMAIN = gangtise_domain("GANGTISE_TOOL_DOMAIN", "https://openapi.gangtise.com/application/open-tool")
WEB_SEARCH_URL = GANGTISE_TOOL_DOMAIN + "/web-search/search"


def _env_truthy(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


GTS_SAVE_FILE = _env_truthy("GTS_SAVE_FILE", False)
GTS_SAVE_EXTENSION = os.getenv("GTS_SAVE_EXTENSION", "md")

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
    import time

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


def dump_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print("检查 gangtise-web 相关配置")
    if not get_authorization_token():
        print("  无法检测到gangtise密钥环境变量或授权文件, gangtise-web 无法正常工作")
    else:
        print("  检测到gangtise授权文件, gangtise-web 可以正常工作")
    if GTS_SAVE_FILE:
        print(f"  环境变量 GTS_SAVE_FILE 为 True, 查询结果将保存为 {GTS_SAVE_EXTENSION}")
    else:
        print("  环境变量 GTS_SAVE_FILE 为 False（未配置或非真值）, 查询结果仅在回复中展示")
    try:
        if check_version(large_version=False):
            print("  gangtise-web 版本为最新")
        else:
            print("  gangtise-web 版本不是最新, 建议进行更新")
    except Exception:
        print("  检查 gangtise-web 版本失败")
    print(f"  gangtise-web 工作文件目录: {gangtise_workspace_path}")
