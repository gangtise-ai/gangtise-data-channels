"""Gangtise OpenAPI 鉴权（skill 独立运行版）。

每个 skill 的 scripts/gts_auth.py 必须逐字节相同，由 scripts/check_skills.py 校验。
CLI / MCP 同步时，`from .gts_auth import` 会被改写为 `from gangtise_core.auth import`，
因此这里导出的名字与签名必须与 core/src/gangtise_core/auth.py 保持一致。

凭证优先级：
1. 环境变量 GTS_AUTHORIZATION / AUTHORIZATION（直接使用 token，不登录）
2. 环境变量 GTS_ACCESS_KEY + GTS_SECRET_KEY → loginV2
3. 凭证文件（authorization 或 accessKey/secretKey）：
   GTS_AUTHORIZATION_PATH > scripts/.authorization > ~/.config/gangtise/authorization

登录得到的 token 缓存在 GTS_TOKEN_CACHE_PATH（默认 ~/.cache/gangtise/token.json），
按 accessKey + 鉴权域名的指纹绑定，换账号不会串 token；格式与 CLI / MCP 共用。
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import os
import stat
import sys
import threading
import time
from typing import Any, Dict, Optional, Tuple

import requests

__all__ = [
    "append_consumed_points_note",
    "append_consumed_points_to_saved_file",
    "apply_consumed_points",
    "authorized_request",
    "consumed_points_seen",
    "format_consumed_points_note",
    "gangtise_domain",
    "get_authorization_headers",
    "get_authorization_token",
    "get_consumed_points",
    "get_headers_extra",
    "invalidate_authorization",
    "take_consumed_points",
]

# OpenAPI 响应头：本次请求实扣积分（尚未全量上线时可能缺失）
CONSUMED_POINT_HEADER = "Consumed-Point"
_consumed_points_total: contextvars.ContextVar[float] = contextvars.ContextVar(
    "gts_consumed_points_total", default=0.0
)
_consumed_points_seen: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "gts_consumed_points_seen", default=False
)

_PROD_PUBLIC_BASE = "https://openapi.gangtise.com/application"
AUTH_EXPIRED_CODES = frozenset({"8000013", "8000014", "999002"})
LOGIN_TIMEOUT = 30
TOKEN_DEFAULT_TTL_SEC = 3600.0
TOKEN_REFRESH_SKEW_SEC = 60.0
DISK_TOKEN_BUFFER_SEC = 300.0

_lock = threading.Lock()
_session: Optional[Dict[str, Any]] = None


def _env(name: str) -> str:
    """空字符串按未设置处理。"""
    return (os.getenv(name) or "").strip()


def _public_default(default: str) -> str:
    """GANGTISE_PUBLIC_BASE 可把生产基址整体换成测试站。"""
    url = (default or "").strip().rstrip("/")
    base = _env("GANGTISE_PUBLIC_BASE").rstrip("/")
    if base and url.startswith(_PROD_PUBLIC_BASE):
        return base + url[len(_PROD_PUBLIC_BASE):]
    return url


def gangtise_domain(env_key: str, default: str) -> str:
    """业务域名：环境变量优先，否则用公网默认值。"""
    return _env(env_key).rstrip("/") or _public_default(default)


def _auth_domain() -> str:
    return gangtise_domain("GANGTISE_AUTH_DOMAIN", f"{_PROD_PUBLIC_BASE}/auth")


def _ensure_bearer(token: Any) -> str:
    text = str(token or "").strip()
    if not text:
        return ""
    return text if text.lower().startswith("bearer ") else f"Bearer {text}"


def _env_authorization() -> str:
    for key in ("GTS_AUTHORIZATION", "AUTHORIZATION"):
        raw = _env(key)
        if raw:
            return _ensure_bearer(raw)
    return ""


def _credential_files() -> Tuple[str, ...]:
    explicit = _env("GTS_AUTHORIZATION_PATH")
    if explicit:
        return (os.path.expanduser(explicit),)
    here = os.path.dirname(os.path.abspath(__file__))
    return (
        os.path.join(here, ".authorization"),
        os.path.join(os.path.expanduser("~"), ".config", "gangtise", "authorization"),
    )


def _read_credential_file() -> Dict[str, Any]:
    for path in _credential_files():
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(content, dict):
            return content
    return {}


def _resolve_credentials() -> Tuple[str, str, str]:
    """返回 (accessKey, secretKey, 文件里的直接 authorization)。"""
    ak, sk = _env("GTS_ACCESS_KEY"), _env("GTS_SECRET_KEY")
    if ak and sk:
        return ak, sk, ""
    content = _read_credential_file()
    file_ak = str(content.get("accessKey") or "").strip()
    file_sk = str(content.get("secretKey") or content.get("secretAccessKey") or "").strip()
    token = _ensure_bearer(content.get("authorization"))
    return ak or file_ak, sk or file_sk, token


def _token_cache_path() -> str:
    explicit = _env("GTS_TOKEN_CACHE_PATH")
    if explicit:
        return os.path.expanduser(explicit)
    return os.path.join(os.path.expanduser("~"), ".cache", "gangtise", "token.json")


def _fingerprint(access_key: str) -> str:
    payload = f"{access_key}\0{_auth_domain()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _load_disk_token(fingerprint: str) -> Optional[Dict[str, Any]]:
    path = _token_cache_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        expires_at = float(cached.get("expires_at") or 0)
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    if cached.get("issued_for") != fingerprint or expires_at - DISK_TOKEN_BUFFER_SEC <= time.time():
        return None
    token = _ensure_bearer(cached.get("authorization"))
    if not token:
        return None
    return {
        "authorization": token,
        "uid": cached.get("uid"),
        "tenantid": cached.get("tenantid"),
        "productcode": cached.get("productcode"),
        "expires_at": expires_at,
    }


def _save_disk_token(session: Dict[str, Any], fingerprint: str) -> None:
    path = _token_cache_path()
    payload = {
        "issued_for": fingerprint,
        "authorization": session.get("authorization"),
        "uid": session.get("uid"),
        "tenantid": session.get("tenantid"),
        "productcode": session.get("productcode"),
        "expires_at": session.get("expires_at"),
    }
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
            f.write("\n")
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp, path)
    except OSError:
        pass


def _expires_at(expires_in: Any) -> float:
    ttl = TOKEN_DEFAULT_TTL_SEC
    if expires_in is not None:
        try:
            ttl = max(60.0, float(expires_in))
        except (TypeError, ValueError):
            pass
    return time.time() + ttl - TOKEN_REFRESH_SKEW_SEC


def _optional_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _login(ak: str, sk: str) -> Optional[Dict[str, Any]]:
    url = f"{_auth_domain()}/oauth/open/loginV2"
    try:
        resp = requests.post(url, json={"accessKey": ak, "secretKey": sk}, timeout=LOGIN_TIMEOUT)
    except requests.RequestException as exc:
        print(f"获取 authorization 失败, 网络错误: {exc}", file=sys.stderr)
        return None
    try:
        body = resp.json()
    except ValueError:
        body = None
    ok = isinstance(body, dict) and body.get("state", body.get("status", True)) is not False
    if resp.status_code != 200 or not ok:
        print(f"获取 authorization 失败, HTTP {resp.status_code}: {resp.text[:300]}", file=sys.stderr)
        return None
    data = body.get("data") if isinstance(body, dict) else None
    token = _ensure_bearer(data.get("accessToken")) if isinstance(data, dict) else ""
    if not token:
        print(f"获取 authorization 失败, 响应格式异常: {resp.text[:300]}", file=sys.stderr)
        return None
    return {
        "authorization": token,
        "uid": _optional_str(data.get("uid")),
        "tenantid": _optional_str(data.get("tenantId")),
        "productcode": _optional_str(data.get("productCode")),
        "expires_at": _expires_at(data.get("expiresIn")),
    }


def _session_fresh(session: Optional[Dict[str, Any]]) -> bool:
    if not session or not session.get("authorization"):
        return False
    exp = session.get("expires_at")
    return exp is None or time.time() < float(exp)


def _build_session(force: bool = False, stale_token: str = "") -> Optional[Dict[str, Any]]:
    """取可用会话。`stale_token` 是刚被服务端拒绝的 token：缓存里若已换成别的就直接用，不重复登录。"""
    global _session
    if not force and _session_fresh(_session):
        return _session
    if stale_token and _session_fresh(_session) and _session.get("authorization") != stale_token:
        return _session
    ak, sk, file_token = _resolve_credentials()
    if ak and sk:
        fingerprint = _fingerprint(ak)
        disk = _load_disk_token(fingerprint)
        if disk is not None and (not force or (stale_token and disk["authorization"] != stale_token)):
            _session = disk
            return _session
        session = _login(ak, sk)
        if session is None:
            _session = None
            return None
        _save_disk_token(session, fingerprint)
        _session = session
        return _session
    _session = {"authorization": file_token} if file_token else None
    return _session


def invalidate_authorization() -> None:
    global _session
    with _lock:
        _session = None


def get_authorization_token() -> Optional[str]:
    env_token = _env_authorization()
    if env_token:
        return env_token
    with _lock:
        session = _build_session()
    return session.get("authorization") if session else None


def get_headers_extra() -> Dict[str, str]:
    """下游业务头 uid / tenantid / productcode：loginV2 会话优先，其次环境变量 UID / TENANTID / PRODUCTCODE。"""
    session: Optional[Dict[str, Any]] = None
    if not _env_authorization():
        with _lock:
            session = _build_session()
    out: Dict[str, str] = {}
    for key, env_key in (("uid", "UID"), ("tenantid", "TENANTID"), ("productcode", "PRODUCTCODE")):
        value = (session or {}).get(key) or _env(env_key)
        if value:
            out[key] = str(value)
    return out


def get_authorization_headers() -> Dict[str, str]:
    token = get_authorization_token()
    extra = get_headers_extra()
    return {"Authorization": token, **extra} if token else extra


def _is_auth_error(response: requests.Response) -> bool:
    if response.status_code == 401:
        return True
    try:
        body = response.json()
    except ValueError:
        return False
    if not isinstance(body, dict):
        return False
    for key in ("code", "errorCode", "errCode"):
        if str(body.get(key, "")).strip() in AUTH_EXPIRED_CODES:
            return True
    error_type = str(body.get("errorType") or "").strip().upper()
    return error_type in {"TOKEN_INVALID", "CREDENTIAL_INVALID", "UNAUTHORIZED"}


def _user_agent() -> str:
    return _env("GTS_USER_AGENT") or "gangtise-skill"


def _parse_consumed_point_header(response: requests.Response) -> Optional[float]:
    """从响应头解析 Consumed-Point；缺失或非法返回 None（不计入 seen）。"""
    raw = response.headers.get(CONSUMED_POINT_HEADER)
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _record_consumed_point(response: requests.Response) -> None:
    value = _parse_consumed_point_header(response)
    if value is None:
        return
    _consumed_points_seen.set(True)
    _consumed_points_total.set(float(_consumed_points_total.get() or 0.0) + value)


def get_consumed_points() -> float:
    return float(_consumed_points_total.get() or 0.0)


def consumed_points_seen() -> bool:
    return bool(_consumed_points_seen.get())


def take_consumed_points() -> Tuple[float, bool]:
    """取出并清零本次脚本调用累计的 Consumed-Point。返回 (total, seen)。"""
    total = get_consumed_points()
    seen = consumed_points_seen()
    _consumed_points_total.set(0.0)
    _consumed_points_seen.set(False)
    return total, seen


def format_consumed_points_note(total: float, *, seen: bool = True) -> str:
    if not seen:
        return ""
    if float(total) == int(total):
        display = str(int(total))
    else:
        display = ("%f" % float(total)).rstrip("0").rstrip(".")
    return f"本次积分消耗：{display}"


def append_consumed_points_note(text: str, note: str) -> str:
    note = (note or "").strip()
    if not note:
        return text or ""
    base = (text or "").rstrip()
    if note in base:
        return base
    return f"{base}\n\n{note}" if base else note


def apply_consumed_points(response: Optional[Dict[str, Any]] = None) -> str:
    """取出累计积分，写入 response['usage']['consumed_point']，返回展示文案（可能为空）。"""
    total, seen = take_consumed_points()
    note = format_consumed_points_note(total, seen=seen)
    if response is not None and seen:
        usage = dict(response.get("usage") or {})
        prev = usage.get("consumed_point")
        try:
            prev_f = float(prev) if prev is not None else 0.0
        except (TypeError, ValueError):
            prev_f = 0.0
        usage["consumed_point"] = prev_f + total
        response["usage"] = usage
    return note


def append_consumed_points_to_saved_file(path: str, note: str) -> None:
    """把积分说明追加到已落盘结果文件（md 正文 / csv 注释行；json 不改结构，改走 .usage）。"""
    note = (note or "").strip()
    if not note or not path:
        return
    lower = path.lower()
    try:
        if lower.endswith(".md"):
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n\n" + note + "\n")
        elif lower.endswith(".csv"):
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n# " + note + "\n")
    except OSError:
        return


def authorized_request(method: str, url: Any, *, retry_on_auth: bool = True, **kwargs: Any) -> requests.Response:
    """带鉴权头发请求；token 失效时换 token 重发一次（直接配置的 token 无法刷新，不重发）。"""
    headers = dict(kwargs.pop("headers", None) or {})
    timeout = kwargs.pop("timeout", 120)
    headers.setdefault("User-Agent", _user_agent())
    headers.update(get_authorization_headers())
    target = str(url)
    response = requests.request(method, target, headers=headers, timeout=timeout, **kwargs)
    if not retry_on_auth or _env_authorization() or not _is_auth_error(response):
        _record_consumed_point(response)
        return response
    stale = headers.get("Authorization", "")
    with _lock:
        session = _build_session(force=True, stale_token=stale)
    if not session or session.get("authorization") == stale:
        _record_consumed_point(response)
        return response
    headers.update(get_authorization_headers())
    response = requests.request(method, target, headers=headers, timeout=timeout, **kwargs)
    _record_consumed_point(response)
    return response
