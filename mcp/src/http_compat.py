"""HTTP 兼容中间件：回传 X-DashScope-Request-ID；注入 Authorization 或 AK/SK。"""
from __future__ import annotations

import base64
import json
import os
import uuid
from typing import Callable, Dict, Optional, Set, Tuple

from starlette.types import ASGIApp, Receive, Scope, Send

DASHSCOPE_REQUEST_ID = "x-dashscope-request-id"

_AUTH_SKIP_PREFIXES = (
    "/.well-known/",
    "/oauth/",
    "/authorize",
    "/token",
    "/register",
    "/health",
)

_CREDENTIALS_HEADER_NAMES = (
    "x-gts-credentials",
    "gts-credentials",
    "x-gangtise-credentials",
)

# 上游网关可能注入、需透传给下游 OpenAPI 的业务头
_FORWARD_EXTRA_HEADER_KEYS = (
    "uid",
    "tenantid",
    "productcode",
)


def env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


def require_auth_enabled() -> bool:
    return env_flag("MCP_REQUIRE_AUTH", "true")


def log_auth_token_enabled() -> bool:
    """输出请求中的 Authorization / 凭证，便于与中台核对 token。默认关闭。"""
    return env_flag("GTS_LOG_AUTH_TOKEN", "false")


# 同一进程内已打印过的 token 指纹，避免 Cursor 一次连接多请求刷屏
_logged_auth_fps: Set[str] = set()


def _log_inbound_auth(
    *,
    path: str,
    request_id: str,
    auth: str,
    creds: Optional[Tuple[str, str]],
    oauth_creds: Optional[Tuple[str, str]],
) -> None:
    if not log_auth_token_enabled():
        return
    if oauth_creds is not None:
        kind = "mcp_oauth_jwt"
        token = auth
    elif auth:
        kind = "authorization_passthrough"
        token = auth
    elif creds is not None:
        kind = "ak_sk"
        token = f"accessKey={creds[0]}"
    else:
        return
    # 按完整 token / AK 去重：同一次 OAuth 会话只打一行
    fp = token
    if fp in _logged_auth_fps:
        return
    _logged_auth_fps.add(fp)
    print(
        f"[gts-auth] request_id={request_id} path={path} kind={kind} token={token}",
        flush=True,
    )


def headers_from_scope(scope: Scope) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for key, value in scope.get("headers") or []:
        out[key.decode("latin-1").lower()] = value.decode("latin-1")
    return out


def client_ip_from_scope(scope: Scope) -> str:
    """按 X-Forwarded-For 等代理头解析本次连接的客户端 IP，没有头时用连接对端。"""
    try:
        from authorization import resolve_client_ip
    except Exception:
        return ""
    client = scope.get("client")
    remote = ""
    if isinstance(client, (list, tuple)) and client:
        remote = str(client[0] or "")
    return resolve_client_ip(headers_from_scope(scope), remote)


def resolve_request_id(headers: Dict[str, str]) -> str:
    rid = (headers.get(DASHSCOPE_REQUEST_ID) or "").strip()
    return rid or str(uuid.uuid4())


def path_skips_auth(path: str) -> bool:
    p = path or "/"
    for prefix in _AUTH_SKIP_PREFIXES:
        if p == prefix.rstrip("/") or p.startswith(prefix):
            return True
    return False


def parse_credentials_payload(raw: str) -> Optional[Tuple[str, str]]:
    text = (raw or "").strip()
    if not text:
        return None
    if not text.startswith("{"):
        try:
            decoded = base64.b64decode(text, validate=True).decode("utf-8")
            if decoded.strip().startswith("{"):
                text = decoded.strip()
        except Exception:
            pass
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    ak = data.get("accessKey") or data.get("access_key")
    sk = data.get("secretKey") or data.get("secret_key") or data.get("secretAccessKey")
    if ak and sk:
        return str(ak).strip(), str(sk).strip()
    return None


def parse_credentials_from_headers(headers: Dict[str, str]) -> Optional[Tuple[str, str]]:
    for name in _CREDENTIALS_HEADER_NAMES:
        if name in headers:
            parsed = parse_credentials_payload(headers[name])
            if parsed:
                return parsed
    ak = (
        headers.get("accesskey")
        or headers.get("access_key")
        or headers.get("x-access-key")
        or headers.get("access-key")
    )
    sk = (
        headers.get("secretkey")
        or headers.get("secret_key")
        or headers.get("x-secret-key")
        or headers.get("secret-key")
        or headers.get("secretaccesskey")
    )
    if ak and sk:
        return ak.strip(), sk.strip()
    return None


def parse_headers_extra_from_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """从入站请求提取 uid / tenantid / productcode（大小写不敏感，已 lower）。"""
    out: Dict[str, str] = {}
    for key in _FORWARD_EXTRA_HEADER_KEYS:
        raw = headers.get(key) or headers.get(f"x-{key}")
        if raw is None:
            continue
        value = str(raw).strip()
        if value:
            out[key] = value
    return out


async def send_json_status(
    send: Send,
    status: int,
    body: dict,
    *,
    request_id: str,
    extra_headers: Optional[list] = None,
) -> None:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (DASHSCOPE_REQUEST_ID.encode("latin-1"), request_id.encode("latin-1")),
        (b"content-length", str(len(payload)).encode("latin-1")),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": headers,
        }
    )
    await send({"type": "http.response.body", "body": payload})


def wrap_send_with_request_id(send: Send, request_id: str) -> Send:
    async def _send(message: dict) -> None:
        if message.get("type") == "http.response.start":
            headers = list(message.get("headers") or [])
            headers = [
                (k, v)
                for k, v in headers
                if k.decode("latin-1").lower() != DASHSCOPE_REQUEST_ID
            ]
            headers.append(
                (DASHSCOPE_REQUEST_ID.encode("latin-1"), request_id.encode("latin-1"))
            )
            message = {**message, "headers": headers}
        await send(message)

    return _send


def oauth_www_authenticate(
    inbound_headers: Dict[str, str],
    *,
    error: Optional[str] = None,
    mcp_source: Optional[str] = None,
) -> list:
    """OAuth 2.1 / RFC 9728：401 带本 MCP 的 resource_metadata。

    客户端据此拉 PR metadata，再按 authorization_servers（中台 GTS_OAUTH_ISSUER）
    去做 refresh / 重新授权。resource_metadata 必须是本资源服务器，不能写成中台 URL。
    有 SUBPATHS 来源时 metadata URL 含 ``/{source}/``，与客户端 MCP 入口一致。
    """
    meta = ""
    try:
        from oauth_server import oauth_challenge_enabled, resource_metadata_url_from_headers

        if not oauth_challenge_enabled():
            return []
        meta = resource_metadata_url_from_headers(inbound_headers, mcp_source=mcp_source)
    except Exception:
        resource = (os.getenv("GTS_OAUTH_RESOURCE") or "").strip().rstrip("/")
        sp = (mcp_source or "").strip().strip("/")
        if resource and sp:
            resource = f"{resource}/{sp}"
        meta = f"{resource}/.well-known/oauth-protected-resource" if resource else ""
    if not meta:
        return []
    params = ['{}="{}"'.format("resource" + "_metadata", meta)]
    if error:
        params.insert(0, f'error="{error}"')
        params.insert(
            1,
            'error_description="Access token rejected; re-authorize at the authorization server"',
        )
    challenge = "Bearer " + ", ".join(params)
    return [(b"www-authenticate", challenge.encode("latin-1"))]


def wrap_send_reauth_challenge(
    send: Send,
    inbound_headers: Dict[str, str],
    *,
    mcp_source: Optional[str] = None,
) -> Send:
    """工具线程里下游 401 后，把尚未发出的 MCP HTTP 响应改成 401 invalid_token。

    客户端应读取 WWW-Authenticate 的 resource_metadata，再去中台 AS 重新授权。
    """

    async def _send(message: dict) -> None:
        if message.get("type") == "http.response.start":
            try:
                from authorization import reauthorization_required

                need = reauthorization_required()
            except Exception:
                need = False
            if need:
                headers = [
                    (k, v)
                    for k, v in list(message.get("headers") or [])
                    if k.decode("latin-1").lower() != "www-authenticate"
                ]
                headers.extend(
                    oauth_www_authenticate(
                        inbound_headers, error="invalid_token", mcp_source=mcp_source
                    )
                )
                message = {**message, "status": 401, "headers": headers}
        await send(message)

    return _send


class HttpMiddleware:
    """回传 Request-ID；注入 Authorization 或 AK/SK；透传 uid/tenantid/productcode。

    鉴权优先级：
    1. 本服务 OAuth access JWT → 解 AK/SK 走 loginV2，并用 JWT claims 补 uid 等
       （内部域名下游需要 uid；网关未强制鉴权时不会再注入）
    2. 其它 Authorization → 原样透传（公网 open-* 下游通常不依赖 uid）
    3. X-GTS-Credentials → AK/SK loginV2
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        set_authorization: Callable[[str], object],
        reset_authorization: Callable[[object], None],
        set_credentials: Optional[Callable[[str, str], object]] = None,
        reset_credentials: Optional[Callable[[object], None]] = None,
        set_headers_extra: Optional[Callable[[Dict[str, str]], object]] = None,
        reset_headers_extra: Optional[Callable[[object], None]] = None,
        mcp_paths: Optional[Set[str]] = None,
    ) -> None:
        self.app = app
        self.set_authorization = set_authorization
        self.reset_authorization = reset_authorization
        self.set_credentials = set_credentials
        self.reset_credentials = reset_credentials
        self.set_headers_extra = set_headers_extra
        self.reset_headers_extra = reset_headers_extra
        self.mcp_paths = mcp_paths or set()

    def _is_mcp_path(self, path: str) -> bool:
        """是否走鉴权。MCP_PATH=/ 时只匹配根路径，避免 startswith('/') 命中全部。"""
        if path_skips_auth(path):
            return False
        if not self.mcp_paths:
            return True
        for p in self.mcp_paths:
            base = "/" if p in ("", "/") else p.rstrip("/")
            if base == "/":
                if path == "/":
                    return True
                continue
            if path == base or path.startswith(base + "/"):
                return True
        return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = headers_from_scope(scope)
        request_id = resolve_request_id(headers)
        mcp_source = ""
        try:
            mcp_source = str((scope.get("state") or {}).get("mcp_source") or "").strip()
        except Exception:
            mcp_source = ""
        send = wrap_send_with_request_id(send, request_id)
        send = wrap_send_reauth_challenge(send, headers, mcp_source=mcp_source or None)

        path = scope.get("path") or "/"
        auth = (headers.get("authorization") or "").strip()
        creds = parse_credentials_from_headers(headers)
        extra = parse_headers_extra_from_headers(headers)

        request_id_token = None
        try:
            from access_log import set_request_id

            request_id_token = set_request_id(request_id)
        except Exception:
            request_id_token = None

        reauth_token = None
        try:
            from authorization import begin_reauthorization_tracker, reset_reauthorization_tracker

            reauth_token = begin_reauthorization_tracker()
        except Exception:
            reauth_token = None

        # Authorization 优先：若为本服务 OAuth access JWT → 解出 AK/SK 走 loginV2；
        # 否则原样透传业务 Bearer；无 Authorization 时用 X-GTS-Credentials。
        # oauth_server 仅整合包存在；其它 api 包 import 失败则走透传/凭证。
        oauth_creds = None
        oauth_identity: Optional[Dict[str, str]] = None
        oauth_class: Optional[str] = None
        ali_invalid_message: Optional[str] = None
        if auth:
            try:
                from oauth_server import (
                    classify_mcp_bearer,
                    try_mcp_oauth_identity,
                    try_mcp_oauth_to_credentials,
                )

                oauth_class = classify_mcp_bearer(auth)
                if oauth_class == "ok":
                    oauth_creds = try_mcp_oauth_to_credentials(auth)
                    oauth_identity = try_mcp_oauth_identity(auth)
            except Exception:
                oauth_creds = None
                oauth_identity = None
                oauth_class = None

            if oauth_class is None and oauth_creds is None:
                try:
                    from ali_mcp_credential import (  # type: ignore[import-not-found]
                        AliMcpCredentialError,
                        is_ali_mcp_token,
                        try_ali_mcp_to_credentials,
                    )
                except ImportError:
                    # 公开仓无对接模块：ali 密文无法解密，若命中前缀则按无效 token 处理
                    try:
                        token_peek = auth.strip()
                        if token_peek.lower().startswith("bearer "):
                            token_peek = token_peek[7:].strip()
                        if token_peek.startswith("ali-mcp-v1."):
                            ali_invalid_message = (
                                "Ali MCP credential decryptor unavailable on this build"
                            )
                    except Exception:
                        pass
                else:
                    try:
                        if is_ali_mcp_token(auth):
                            oauth_creds = try_ali_mcp_to_credentials(auth)
                            if not oauth_creds:
                                ali_invalid_message = "Ali MCP token decrypt returned empty credentials"
                    except Exception as exc:
                        # AliMcpCredentialError 及其它解密异常 → 401
                        name = type(exc).__name__
                        if name == "AliMcpCredentialError" or isinstance(
                            exc, AliMcpCredentialError
                        ):
                            ali_invalid_message = str(exc) or "Ali MCP token decrypt failed"
                        else:
                            ali_invalid_message = f"Ali MCP token decrypt failed: {exc}"

        if (
            (oauth_class == "invalid" or ali_invalid_message)
            and require_auth_enabled()
            and self._is_mcp_path(path)
        ):
            err_desc = ali_invalid_message or "OAuth access token expired or invalid"
            try:
                from access_log import write_event

                write_event(
                    "mcp_error",
                    where="http_auth",
                    path=path,
                    source=mcp_source or "",
                    error_code="UNAUTHORIZED",
                    error_message=err_desc,
                )
            except Exception:
                pass
            await send_json_status(
                send,
                401,
                {
                    "error": "invalid_token",
                    "error_description": err_desc,
                    "code": "UNAUTHORIZED",
                },
                request_id=request_id,
                extra_headers=oauth_www_authenticate(
                    headers, error="invalid_token", mcp_source=mcp_source or None
                ),
            )
            if reauth_token is not None:
                try:
                    from authorization import reset_reauthorization_tracker

                    reset_reauthorization_tracker(reauth_token)
                except Exception:
                    pass
            if request_id_token is not None:
                try:
                    from access_log import reset_request_id

                    reset_request_id(request_id_token)
                except Exception:
                    pass
            return

        # 内部域名下游需要 uid：网关未鉴权时不会注入，从 OAuth JWT claims 补齐
        if oauth_identity:
            for key, value in oauth_identity.items():
                extra.setdefault(key, value)

        if self._is_mcp_path(path) and (auth or creds or oauth_creds):
            _log_inbound_auth(
                path=path,
                request_id=request_id,
                auth=auth,
                creds=creds,
                oauth_creds=oauth_creds,
            )

        auth_token = None
        cred_token = None
        extra_token = None
        if oauth_creds and self.set_credentials is not None:
            cred_token = self.set_credentials(oauth_creds[0], oauth_creds[1])
        elif auth:
            auth_token = self.set_authorization(auth)
        elif creds and self.set_credentials is not None:
            cred_token = self.set_credentials(creds[0], creds[1])
        if extra and self.set_headers_extra is not None:
            extra_token = self.set_headers_extra(extra)

        has_auth = bool(auth or creds or oauth_creds)
        if require_auth_enabled() and self._is_mcp_path(path) and not has_auth:
            try:
                from access_log import write_event

                write_event(
                    "mcp_error",
                    where="http_auth",
                    path=path,
                    source=mcp_source or "",
                    error_code="UNAUTHORIZED",
                    error_message="Missing Authorization or credentials headers",
                )
            except Exception:
                pass
            await send_json_status(
                send,
                401,
                {
                    "error": "unauthorized",
                    "message": "Missing Authorization or credentials headers",
                    "code": "UNAUTHORIZED",
                },
                request_id=request_id,
                extra_headers=oauth_www_authenticate(
                    headers, mcp_source=mcp_source or None
                ),
            )
            if reauth_token is not None:
                try:
                    from authorization import reset_reauthorization_tracker

                    reset_reauthorization_tracker(reauth_token)
                except Exception:
                    pass
            if request_id_token is not None:
                try:
                    from access_log import reset_request_id

                    reset_request_id(request_id_token)
                except Exception:
                    pass
            return

        client_ip_token = None
        client_ip = client_ip_from_scope(scope)
        if client_ip:
            try:
                from authorization import set_request_client_ip

                client_ip_token = set_request_client_ip(client_ip)
            except Exception:
                client_ip_token = None

        source_token = None
        try:
            from subpath_routing import set_request_mcp_source

            source_token = set_request_mcp_source(mcp_source)
        except Exception:
            source_token = None

        try:
            await self.app(scope, receive, send)
        finally:
            if auth_token is not None:
                self.reset_authorization(auth_token)
            if cred_token is not None and self.reset_credentials is not None:
                self.reset_credentials(cred_token)
            if extra_token is not None and self.reset_headers_extra is not None:
                self.reset_headers_extra(extra_token)
            if client_ip_token is not None:
                try:
                    from authorization import reset_request_client_ip

                    reset_request_client_ip(client_ip_token)
                except Exception:
                    pass
            if source_token is not None:
                try:
                    from subpath_routing import reset_request_mcp_source

                    reset_request_mcp_source(source_token)
                except Exception:
                    pass
            if reauth_token is not None:
                try:
                    from authorization import reset_reauthorization_tracker

                    reset_reauthorization_tracker(reauth_token)
                except Exception:
                    pass
            if request_id_token is not None:
                try:
                    from access_log import reset_request_id

                    reset_request_id(request_id_token)
                except Exception:
                    pass
