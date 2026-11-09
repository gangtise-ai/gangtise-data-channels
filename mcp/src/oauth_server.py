"""MCP OAuth 2.1 Authorization Server（WorkBuddy / Cursor 等客户端）。

环境变量：
  GTS_JWT_SECRET     — 必填（启用本机 OAuth AS）；任意长度字符串，内部 SHA-256 后作 HMAC 密钥
  GTS_CRED_ENC_KEY   — 可选；Fernet key，缺省由 JWT secret 派生
  GTS_OAUTH_RESOURCE — MCP Protected Resource 基址（启动变量；不含 SUBPATHS 来源段）
                       须与客户端配置的 MCP 基址一致；有来源子路径时运行时拼成
                       {resource}/{source}/（例：…/open-mcp/kimi/）
                       未设则按请求 Host / X-Forwarded-* 推断
                       例：https://open.gangtise.com/application/open-mcp
  GTS_OAUTH_ISSUER   — 授权服务器 issuer（authorization_servers）；可与 resource 不同（中台独立 AS）
                       未设时回退为本服务公网基址
                       与本服务 resource 不同时：本机只做 Protected Resource，
                       MCP 路径下的 /oauth/*、well-known 发现文档转发到 UPSTREAM，
                       /oauth/authorize GET 302 到公网 ISSUER（浏览器打不开内网）
                       （兼容 Cherry / WorkBuddy 等对 MCP 主机直接探 AS 的客户端）
                       例：https://auth.gangtise.com
  GTS_OAUTH_UPSTREAM — 外部 AS 时本机转发基址（可与 ISSUER 不同）
                       默认 https://auth.gangtise.com
                       集群内建议填内网，例：
                       http://workbuddy-connector-server.platform-business:15684
  GTS_OAUTH_SCOPES   — PR metadata 的 scopes_supported，逗号或空格分隔，默认 mcp；
                       使用外部 AS 时须与其 scopes_supported 一致，例：mcp.read mcp.write
  GTS_OAUTH_ACCESS_TTL   — access 秒数，默认 3600
  GTS_OAUTH_REFRESH_TTL  — refresh 秒数，默认 7 天
  GTS_OAUTH_RATE_LIMIT   — 同意页 POST 每 IP 窗口内最大次数，默认 10（0=关闭）
  GTS_OAUTH_RATE_WINDOW  — 限流窗口秒数，默认 300
  GTS_OAUTH_CAPTCHA      — 同意页算术验证码，默认 true
  GTS_OAUTH_PENDING_TTL  — 未完成授权的 client 保留秒数，默认 600；超时主动清理
  GTS_OAUTH_PENDING_MAX  — 未完成授权（注册页进行中）最大同时数，默认 10000

端点（规范路径 + README 回退别名）：
  GET  /.well-known/oauth-protected-resource
  GET  /.well-known/oauth-authorization-server
  GET  /.well-known/openid-configuration
  POST /oauth/register  | /register
  GET/POST /oauth/authorize | /authorize
  POST /oauth/token     | /token

同意页收集开放平台 AK/SK，校验 loginV2 后签发 access（1h）/ refresh（7d）。
客户端携带的 MCP access JWT 由 http_compat 解出 AK/SK，再走现有 loginV2 调业务。
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import secrets
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urlparse

import jwt
from cryptography.fernet import Fernet, InvalidToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from authorization import AUTHORIZATION_URL, _login

ACCESS_TTL_SEC = int(os.getenv("GTS_OAUTH_ACCESS_TTL", "3600"))
REFRESH_TTL_SEC = int(os.getenv("GTS_OAUTH_REFRESH_TTL", str(7 * 24 * 3600)))
CODE_TTL_SEC = 600
CAPTCHA_TTL_SEC = 600
JWT_ALG = "HS256"
JWT_ISS_CLAIM = "gts_mcp"
DEFAULT_OAUTH_UPSTREAM = "https://auth.gangtise.com"

# 转发到中台 AS 时透传的客户端 IP / 代理链头（大小写不敏感匹配入站）
_PROXY_IP_HEADER_NAMES = (
    "x-forwarded-for",
    "x-real-ip",
    "proxy-client-ip",
    "wl-proxy-client-ip",
    "http_client_ip",
    "http_x_forwarded_for",
    "forwarded",
    "x-forwarded-proto",
    "x-forwarded-host",
    "x-forwarded-port",
)

_CONSENT_TEMPLATE_PATH = Path(__file__).resolve().parent / "oauth_consent.html"
_consent_template_cache: Optional[str] = None

# captcha_id -> {answer, exp}
_captchas: Dict[str, Dict[str, Any]] = {}
# rate key -> timestamps
_rate_hits: Dict[str, Deque[float]] = defaultdict(deque)


def _env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


def captcha_enabled() -> bool:
    return _env_flag("GTS_OAUTH_CAPTCHA", "true")


def _rate_limit_max() -> int:
    try:
        return max(0, int(os.getenv("GTS_OAUTH_RATE_LIMIT", "10")))
    except ValueError:
        return 10


def _rate_window_sec() -> int:
    try:
        return max(1, int(os.getenv("GTS_OAUTH_RATE_WINDOW", "300")))
    except ValueError:
        return 300


def _client_ip(request: Request) -> str:
    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        return xff.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _rate_allow(bucket: str, *, cost: int = 1) -> bool:
    """滑动窗口限流；返回是否允许。max=0 表示关闭。"""
    limit = _rate_limit_max()
    if limit <= 0:
        return True
    now = time.time()
    window = float(_rate_window_sec())
    q = _rate_hits[bucket]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) + cost > limit:
        return False
    for _ in range(cost):
        q.append(now)
    return True


def _prune_captchas(now: Optional[float] = None) -> None:
    t = now if now is not None else time.time()
    dead = [k for k, v in _captchas.items() if float(v.get("exp") or 0) < t]
    for k in dead:
        _captchas.pop(k, None)


def _issue_captcha() -> Tuple[str, str]:
    """返回 (captcha_id, question_text)。"""
    _prune_captchas()
    a = secrets.randbelow(8) + 2
    b = secrets.randbelow(8) + 2
    cid = secrets.token_urlsafe(18)
    _captchas[cid] = {"answer": str(a + b), "exp": time.time() + CAPTCHA_TTL_SEC}
    return cid, f"{a} + {b} = ?"


def _verify_captcha(captcha_id: str, answer: str) -> bool:
    if not captcha_enabled():
        return True
    cid = (captcha_id or "").strip()
    ans = (answer or "").strip()
    if not cid or not ans:
        return False
    entry = _captchas.pop(cid, None)
    if not entry:
        return False
    if float(entry.get("exp") or 0) < time.time():
        return False
    return str(entry.get("answer")) == ans


def _load_consent_template() -> str:
    global _consent_template_cache
    if _consent_template_cache is None:
        _consent_template_cache = _CONSENT_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _consent_template_cache


def _consent_html(
    *,
    error: str = "",
    client_id: str = "",
    redirect_uri: str = "",
    state: str = "",
    code_challenge: str = "",
    code_challenge_method: str = "S256",
    scope: str = "mcp",
    captcha_id: str = "",
    captcha_question: str = "",
) -> str:
    if captcha_enabled():
        if not captcha_id:
            captcha_id, captcha_question = _issue_captcha()
        captcha_block = (
            '<label for="captcha_answer">验证码</label>'
            '<div class="captcha-row">'
            f'<div class="captcha-q" aria-hidden="true">{html.escape(captcha_question)}</div>'
            '<input id="captcha_answer" name="captcha_answer" type="text" inputmode="numeric" '
            'required autocomplete="off" placeholder="计算结果" style="flex:1"/>'
            "</div>"
        )
    else:
        captcha_id = ""
        captcha_block = ""
    err_block = f'<p class="err">{html.escape(error)}</p>' if error else ""
    return (
        _load_consent_template()
        .replace("{{ERROR_BLOCK}}", err_block)
        .replace("{{CLIENT_ID}}", html.escape(client_id, quote=True))
        .replace("{{REDIRECT_URI}}", html.escape(redirect_uri, quote=True))
        .replace("{{STATE}}", html.escape(state, quote=True))
        .replace("{{CODE_CHALLENGE}}", html.escape(code_challenge, quote=True))
        .replace("{{CODE_CHALLENGE_METHOD}}", html.escape(code_challenge_method, quote=True))
        .replace("{{SCOPE}}", html.escape(scope, quote=True))
        .replace("{{CAPTCHA_ID}}", html.escape(captcha_id, quote=True))
        .replace("{{CAPTCHA_BLOCK}}", captcha_block)
    )


def oauth_enabled() -> bool:
    """本机 OAuth AS（同意页 / token）需要 GTS_JWT_SECRET。

    若配置了外部 GTS_OAUTH_ISSUER（与本服务 resource 不同），本机不再充当 AS，
    此时即使设了 GTS_JWT_SECRET 也不启用本机 register/authorize/token。
    """
    if not (os.getenv("GTS_JWT_SECRET") or "").strip():
        return False
    # 启动期无 Request 时按环境变量判断；与 uses_external_authorization_server 一致
    if uses_external_authorization_server(None):
        return False
    return True


def oauth_challenge_enabled() -> bool:
    """是否对外发出 OAuth 2.1 401 挑战 / PR metadata（中台 AS 不依赖本机 JWT）。"""
    if oauth_enabled():
        return True
    if (os.getenv("GTS_OAUTH_ISSUER") or "").strip():
        return True
    if (os.getenv("GTS_OAUTH_RESOURCE") or "").strip():
        return True
    return False


def resolve_oauth_upstream() -> str:
    """外部 AS 转发基址（无尾斜杠）。

    优先 GTS_OAUTH_UPSTREAM；未设时回退 GTS_OAUTH_ISSUER；再回退公网默认。
    浏览器 302 / authorization_servers 仍用 resolve_public_base（ISSUER），不要用内网 upstream。
    """
    explicit = (os.getenv("GTS_OAUTH_UPSTREAM") or "").strip().rstrip("/")
    if explicit:
        return explicit
    issuer = (os.getenv("GTS_OAUTH_ISSUER") or "").strip().rstrip("/")
    if issuer:
        return issuer
    return DEFAULT_OAUTH_UPSTREAM


def _join_upstream_path(base: str, path: str) -> str:
    root = (base or "").rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return f"{root}{path}"


def _external_as_public_endpoint(request: Optional[Request], path: str) -> str:
    """浏览器 / 元数据用的公网 AS 端点（GTS_OAUTH_ISSUER）。"""
    return _join_upstream_path(resolve_public_base(request), path)


def _external_as_upstream_endpoint(path: str) -> str:
    """集群内转发用的 AS 端点（GTS_OAUTH_UPSTREAM）。"""
    return _join_upstream_path(resolve_oauth_upstream(), path)


def _proxy_forward_headers(request: Request) -> Dict[str, str]:
    """组装转发头：业务头 + 入站 IP/代理链头；缺 XFF 时用解析出的客户端 IP 补上。"""
    headers: Dict[str, str] = {}
    if request.headers.get("content-type"):
        headers["Content-Type"] = request.headers["content-type"]
    if request.headers.get("accept"):
        headers["Accept"] = request.headers["accept"]
    if request.headers.get("authorization"):
        headers["Authorization"] = request.headers["authorization"]

    present = {k.lower() for k in headers}
    for name in _PROXY_IP_HEADER_NAMES:
        if name in present:
            continue
        raw = request.headers.get(name)
        if raw is None or not str(raw).strip():
            continue
        # 保留常见规范大小写，便于下游识别
        if name == "x-forwarded-for":
            out_name = "X-Forwarded-For"
        elif name == "x-real-ip":
            out_name = "X-Real-IP"
        elif name == "x-forwarded-proto":
            out_name = "X-Forwarded-Proto"
        elif name == "x-forwarded-host":
            out_name = "X-Forwarded-Host"
        elif name == "x-forwarded-port":
            out_name = "X-Forwarded-Port"
        elif name == "forwarded":
            out_name = "Forwarded"
        else:
            out_name = "-".join(p.capitalize() for p in name.split("-"))
        headers[out_name] = str(raw).strip()
        present.add(name)

    try:
        from authorization import apply_downstream_headers

        apply_downstream_headers(headers)
    except Exception:
        pass

    # 入站无任何 IP 头、ContextVar 也未写入时，用连接对端兜底
    if not any(k.lower() == "x-forwarded-for" for k in headers):
        ip = _client_ip(request)
        if ip and ip != "unknown":
            headers["X-Forwarded-For"] = ip
    return headers


async def _proxy_external_as(request: Request, path: str) -> Response:
    """把本机 AS 路径转发到中台（Cherry / WorkBuddy 等常对 MCP 主机探 OAuth）。

    不在本机签发 client_id；响应体原样来自中台。Host 由 upstream URL 决定，不透传入站 Host。
    """
    import requests

    url = _external_as_upstream_endpoint(path)
    body = await request.body()
    headers = _proxy_forward_headers(request)
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            params=list(request.query_params.multi_items()),
            data=body if body else None,
            headers=headers,
            timeout=45,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        return JSONResponse(
            {
                "error": "temporarily_unavailable",
                "error_description": f"external authorization server unreachable: {exc}",
            },
            status_code=502,
        )
    media = (resp.headers.get("Content-Type") or "application/json").split(";")[0].strip()
    out_headers: Dict[str, str] = {}
    # 浏览器授权偶发经本机 POST 代理时，透传 Location
    location = resp.headers.get("Location")
    if location:
        out_headers["Location"] = location
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=media or None,
        headers=out_headers or None,
    )


def _redirect_external_authorize(request: Request) -> RedirectResponse:
    """浏览器授权：302 到公网 ISSUER（不要跳内网 UPSTREAM），带上原 query。"""
    target = _external_as_public_endpoint(request, "/oauth/authorize")
    q = request.url.query
    if q:
        target = f"{target}?{q}"
    return RedirectResponse(url=target, status_code=302)


def _is_cluster_or_pod_host(host: str) -> bool:
    """K8s 内网 Host，不能当作对外公网基址。"""
    h = (host or "").split(":")[0].strip().lower()
    if not h:
        return True
    return (
        h.endswith(".svc")
        or h.endswith(".cluster.local")
        or h.endswith(".svc.cluster.local")
        or h == "gangtise-mcp"
    )


def _headers_from_request(request: Optional[Request]) -> Dict[str, str]:
    if request is None:
        return {}
    try:
        return {k.lower(): v for k, v in request.headers.items()}
    except Exception:
        headers: Dict[str, str] = {}
        for k, v in request.scope.get("headers") or []:
            key = k.decode("latin-1").lower() if isinstance(k, bytes) else str(k).lower()
            val = v.decode("latin-1") if isinstance(v, bytes) else str(v)
            headers[key] = val
        return headers


def _infer_public_base_from_headers(
    headers: Dict[str, str],
    *,
    scheme_default: str = "http",
) -> str:
    """按请求 Host / X-Forwarded-* 推断本服务公网基址（无尾斜杠）。"""
    h = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    xf_proto = (h.get("x-forwarded-proto") or "").split(",")[0].strip()
    xf_host = (h.get("x-forwarded-host") or "").split(",")[0].strip()
    xf_prefix = (
        h.get("x-forwarded-prefix") or os.getenv("GTS_OAUTH_PATH_PREFIX") or ""
    ).strip().rstrip("/")
    host = xf_host or (h.get("host") or "").strip()
    proto = xf_proto or scheme_default or "http"

    if host and not _is_cluster_or_pod_host(host):
        path = xf_prefix or ""
        return f"{proto}://{host}{path}".rstrip("/")

    return "http://localhost:8000"


def resolve_service_public_base(request: Optional[Request] = None) -> str:
    """本 MCP 服务公网基址（无尾斜杠，不含 SUBPATHS 来源段）。

    优先 GTS_OAUTH_RESOURCE，否则按请求推断。
    """
    if request is not None:
        return resolve_service_public_base_from_headers(
            _headers_from_request(request),
            scheme_default=request.url.scheme or "http",
        )
    return resolve_service_public_base_from_headers({})


def resolve_service_public_base_from_headers(
    headers: Dict[str, str],
    *,
    scheme_default: str = "http",
) -> str:
    explicit = (os.getenv("GTS_OAUTH_RESOURCE") or "").strip().rstrip("/")
    if explicit:
        return explicit
    return _infer_public_base_from_headers(headers, scheme_default=scheme_default)


def mcp_source_from_request(request: Optional[Request] = None) -> str:
    """SubpathMiddleware 写入的来源段（如 kimi）；无则空串。

    Starlette 会把 ``scope["state"]`` 包成 ``State``（无 ``.get``），须按属性读。
    """
    if request is None:
        return ""
    try:
        state = request.scope.get("state")
        if state is None:
            return ""
        if isinstance(state, dict):
            raw = state.get("mcp_source")
        else:
            raw = getattr(state, "mcp_source", None)
        return str(raw or "").strip().strip("/")
    except Exception:
        return ""


def with_mcp_source(base: str, source: Optional[str] = None) -> str:
    """把 SUBPATHS 来源拼到 resource 基址上（无尾斜杠）。"""
    root = (base or "").rstrip("/")
    sp = (source or "").strip().strip("/")
    if not root:
        return f"/{sp}" if sp else ""
    if not sp:
        return root
    return f"{root}/{sp}"


def resolve_public_base(request: Optional[Request] = None) -> str:
    """授权服务器 issuer 基址（无尾斜杠）。

    优先 GTS_OAUTH_ISSUER；未配置时回退为本服务公网基址。
    """
    if request is not None:
        return resolve_public_base_from_headers(
            _headers_from_request(request),
            scheme_default=request.url.scheme or "http",
        )
    return resolve_public_base_from_headers({})


def resolve_public_base_from_headers(
    headers: Dict[str, str],
    *,
    scheme_default: str = "http",
) -> str:
    explicit = (os.getenv("GTS_OAUTH_ISSUER") or "").strip().rstrip("/")
    if explicit:
        return explicit
    return resolve_service_public_base_from_headers(headers, scheme_default=scheme_default)


def get_issuer(request: Optional[Request] = None) -> str:
    """兼容旧调用；新代码请传 request。"""
    return resolve_public_base(request)


def public_resource_url(
    request: Optional[Request] = None,
    *,
    mcp_source: Optional[str] = None,
) -> str:
    """MCP resource 标识，须与客户端配置的 MCP URL 一致（通常带尾 /）。

    含 SUBPATHS 来源时为 ``{GTS_OAUTH_RESOURCE}/{source}/``。
    """
    source = mcp_source if mcp_source is not None else mcp_source_from_request(request)
    return with_mcp_source(resolve_service_public_base(request), source) + "/"


def resource_metadata_url(
    request: Optional[Request] = None,
    *,
    mcp_source: Optional[str] = None,
) -> str:
    """PR metadata 位于本服务（非外部 issuer）；路径含来源子路径以便客户端按入口拉取。"""
    source = mcp_source if mcp_source is not None else mcp_source_from_request(request)
    return (
        with_mcp_source(resolve_service_public_base(request), source)
        + "/.well-known/oauth-protected-resource"
    )


def resource_metadata_url_from_headers(
    headers: Dict[str, str],
    *,
    scheme_default: str = "http",
    mcp_source: Optional[str] = None,
) -> str:
    base = resolve_service_public_base_from_headers(headers, scheme_default=scheme_default)
    return with_mcp_source(base, mcp_source) + "/.well-known/oauth-protected-resource"


def uses_external_authorization_server(request: Optional[Request] = None) -> bool:
    """GTS_OAUTH_ISSUER 指向中台等外部 AS 时，本服务只做 Protected Resource。"""
    issuer = resolve_public_base(request).rstrip("/")
    resource = resolve_service_public_base(request).rstrip("/")
    return bool(issuer) and issuer != resource


def _jwt_secret() -> bytes:
    """HMAC 密钥：对配置串做 SHA-256，固定 32 字节，避免 PyJWT InsecureKeyLengthWarning。"""
    secret = (os.getenv("GTS_JWT_SECRET") or "").strip()
    if not secret:
        raise RuntimeError("GTS_JWT_SECRET is not set")
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _fernet() -> Fernet:
    raw = (os.getenv("GTS_CRED_ENC_KEY") or "").strip()
    if raw:
        return Fernet(raw.encode("utf-8"))
    # 与 JWT 同源派生，保证未单独配置 CRED_ENC_KEY 时行为稳定
    return Fernet(base64.urlsafe_b64encode(_jwt_secret()))


def _encrypt_creds(ak: str, sk: str) -> str:
    payload = json.dumps({"accessKey": ak, "secretKey": sk}, ensure_ascii=False).encode("utf-8")
    return _fernet().encrypt(payload).decode("utf-8")


def _decrypt_creds(token: str) -> Optional[Tuple[str, str]]:
    try:
        raw = _fernet().decrypt(token.encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))
        ak = str(data.get("accessKey") or "").strip()
        sk = str(data.get("secretKey") or "").strip()
        if ak and sk:
            return ak, sk
    except (InvalidToken, ValueError, json.JSONDecodeError, TypeError):
        return None
    return None


def _decode_mcp_jwt(token: str) -> Dict[str, Any]:
    """解码本服务签发的 JWT；必须传 audience，否则 PyJWT 对含 aud 的 token 直接 InvalidAudienceError。"""
    return jwt.decode(
        token,
        _jwt_secret(),
        algorithms=[JWT_ALG],
        audience=JWT_ISS_CLAIM,
        options={"require": ["exp", "iat", "typ"]},
    )


def try_mcp_oauth_to_credentials(authorization: str) -> Optional[Tuple[str, str]]:
    """若 Authorization 为本服务签发的 access JWT，返回 (ak, sk)；否则 None。"""
    claims = _try_decode_access_claims(authorization)
    if not claims:
        return None
    cred = claims.get("cred")
    if not isinstance(cred, str):
        return None
    return _decrypt_creds(cred)


def try_mcp_oauth_identity(authorization: str) -> Optional[Dict[str, str]]:
    """从本服务 access JWT 取出 uid/tenantid/productcode（若有）。"""
    claims = _try_decode_access_claims(authorization)
    if not claims:
        return None
    out: Dict[str, str] = {}
    for key in ("uid", "tenantid", "productcode"):
        val = claims.get(key)
        if val is not None and str(val).strip():
            out[key] = str(val).strip()
    return out or None


def _try_decode_access_claims(authorization: str) -> Optional[Dict[str, Any]]:
    if classify_mcp_bearer(authorization) != "ok":
        return None
    token = (authorization or "").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    try:
        claims = _decode_mcp_jwt(token)
    except jwt.PyJWTError:
        return None
    if claims.get("typ") != "access":
        return None
    return claims


def classify_mcp_bearer(authorization: str) -> Optional[str]:
    """区分本服务 OAuth access JWT 与其它 Bearer。

    返回：
      ``ok``       — 签名/audience/typ 有效且未过期
      ``invalid``  — 确为本服务签发，但过期、typ 不对或 cred 解不开（应 401 invalid_token）
      ``None``     — 不是本服务 JWT，走业务 token 透传
    """
    if not oauth_enabled():
        return None
    token = (authorization or "").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not token or token.count(".") != 2:
        return None
    try:
        claims = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[JWT_ALG],
            audience=JWT_ISS_CLAIM,
            options={"require": ["iat", "typ"], "verify_exp": False},
        )
    except jwt.PyJWTError:
        return None
    if claims.get("typ") != "access":
        return "invalid"
    try:
        exp = int(claims.get("exp") or 0)
    except (TypeError, ValueError):
        return "invalid"
    if exp < time.time():
        return "invalid"
    cred = claims.get("cred")
    if not isinstance(cred, str) or not _decrypt_creds(cred):
        return "invalid"
    return "ok"


# --- in-memory stores (单副本部署足够；多副本需外置) ---
# client: status=pending|completed；completed 永久保留，pending 超时清理且有上限
_clients: Dict[str, Dict[str, Any]] = {}
_auth_codes: Dict[str, Dict[str, Any]] = {}


def _pending_ttl_sec() -> int:
    try:
        return max(1, int(os.getenv("GTS_OAUTH_PENDING_TTL", "600")))
    except ValueError:
        return 600


def _pending_max() -> int:
    try:
        return max(1, int(os.getenv("GTS_OAUTH_PENDING_MAX", "10000")))
    except ValueError:
        return 10000


def _prune_pending_clients(now: Optional[float] = None) -> int:
    """清理超时未完成授权的 client；顺带丢掉过期 auth code。返回清理的 client 数。"""
    t = now if now is not None else time.time()
    ttl = float(_pending_ttl_sec())
    dead = [
        cid
        for cid, c in _clients.items()
        if c.get("status", "pending") != "completed"
        and t - float(c.get("touch_at") or c.get("created_at") or 0) > ttl
    ]
    for cid in dead:
        _clients.pop(cid, None)
    expired_codes = [c for c, e in _auth_codes.items() if float(e.get("exp") or 0) < t]
    for c in expired_codes:
        _auth_codes.pop(c, None)
    return len(dead)


def _pending_client_count() -> int:
    return sum(1 for c in _clients.values() if c.get("status", "pending") != "completed")


def _touch_client(client_id: str) -> None:
    entry = _clients.get(client_id)
    if entry and entry.get("status") != "completed":
        entry["touch_at"] = time.time()


def _mark_client_completed(client_id: str) -> None:
    """同意页 AK/SK 成功并签发 authorization code 后标记完成，永久保留。"""
    if not client_id:
        return
    entry = _clients.get(client_id)
    if not entry:
        return
    entry["status"] = "completed"
    entry["completed_at"] = time.time()
    entry["touch_at"] = entry["completed_at"]


def _put_pending_client(
    *,
    client_id: str,
    redirect_uris: List[str],
    client_name: str = "mcp-client",
) -> Optional[str]:
    """登记或刷新 pending client。超额返回 None（调用方应拒绝）。已 completed 的只更新 redirect。"""
    _prune_pending_clients()
    now = time.time()
    existing = _clients.get(client_id)
    if existing and existing.get("status") == "completed":
        uris = existing.setdefault("redirect_uris", [])
        for u in redirect_uris:
            if u and u not in uris:
                uris.append(u)
        return client_id

    if existing:
        # 已有 pending：刷新活跃时间，必要时补 redirect
        existing["touch_at"] = now
        uris = existing.setdefault("redirect_uris", [])
        for u in redirect_uris:
            if u and u not in uris:
                uris.append(u)
        if client_name:
            existing["client_name"] = client_name
        return client_id

    if _pending_client_count() >= _pending_max():
        return None

    _clients[client_id] = {
        "client_id": client_id,
        "redirect_uris": list(redirect_uris),
        "client_name": client_name or "mcp-client",
        "token_endpoint_auth_method": "none",
        "status": "pending",
        "created_at": now,
        "touch_at": now,
    }
    return client_id


def _client_capacity_error(*, as_html: bool = False) -> Response:
    desc = (
        f"pending OAuth registrations full (max {_pending_max()}); "
        f"incomplete entries expire after {_pending_ttl_sec()}s"
    )
    if as_html:
        return HTMLResponse(
            _consent_html(error="授权通道繁忙，请稍后再试（未完成注册会在超时后自动释放）"),
            status_code=503,
        )
    return JSONResponse(
        {"error": "temporarily_unavailable", "error_description": desc},
        status_code=503,
    )


def _pkce_s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _validate_redirect_uri(uri: str) -> bool:
    """允许的回调：

    - WorkBuddy 私有协议：workbuddy://workbuddy/mcp/connector:<source>/oauth/callback
    - WorkBuddy / 规范本机：http://127.0.0.1|localhost:{port}/oauth/callback
    - Cursor 桌面：http://127.0.0.1|localhost:{port}/callback（常见 8787）
    - Cursor 自定义协议 / Web Agents（DCR 常一并提交）
    """
    try:
        p = urlparse(uri)
    except Exception:
        return False
    host = (p.hostname or "").lower()
    path = (p.path or "").rstrip("/") or "/"

    # WorkBuddy：私有协议优先；私有协议被拒时会回退本机 http 回调
    if p.scheme == "workbuddy" and host == "workbuddy":
        return path.endswith("/oauth/callback") or "/oauth/callback" in path

    # Cursor / 部分客户端在 DCR 时会带多条 redirect_uris，需全部通过校验
    if p.scheme == "cursor" and host in ("anysphere.cursor-mcp",) and path == "/oauth/callback":
        return True
    if (
        p.scheme == "https"
        and host in ("www.cursor.com", "cursor.com")
        and path == "/agents/mcp/oauth/callback"
    ):
        return True

    if p.scheme != "http" or host not in ("127.0.0.1", "localhost"):
        return False
    if path not in ("/oauth/callback", "/callback"):
        return False
    # 本机回调应带端口（Cursor 固定 8787；WorkBuddy 动态端口）
    if p.port is None:
        return False
    return True


def _redirect_uri_error_description() -> str:
    return (
        "redirect_uri must be loopback http://127.0.0.1|localhost:{port}/oauth/callback|/callback, "
        "or workbuddy://workbuddy/mcp/connector:<source>/oauth/callback, "
        "or cursor://anysphere.cursor-mcp/oauth/callback, "
        "or https://www.cursor.com/agents/mcp/oauth/callback"
    )


def _disabled() -> JSONResponse:
    return JSONResponse(
        {
            "error": "temporarily_unavailable",
            "error_description": "OAuth is not configured (set GTS_OAUTH_ISSUER or GTS_JWT_SECRET)",
        },
        status_code=503,
    )


async def oauth_protected_resource(request: Request) -> Response:
    if not oauth_challenge_enabled():
        return _disabled()
    # resource = 本 MCP；authorization_servers = 中台 AS（GTS_OAUTH_ISSUER）或本机
    as_issuer = resolve_public_base(request)
    resource = public_resource_url(request)
    return JSONResponse(
        {
            "resource": resource,
            "authorization_servers": [as_issuer],
            "bearer_methods_supported": ["header"],
            "scopes_supported": _resource_scopes(),
        }
    )


def _resource_scopes() -> list:
    raw = (os.getenv("GTS_OAUTH_SCOPES") or "").replace(",", " ").split()
    return raw or ["mcp"]


def _authorization_server_metadata(issuer: str) -> dict:
    issuer = issuer.rstrip("/")
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "registration_endpoint": f"{issuer}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": _resource_scopes(),
    }


async def oauth_authorization_server(request: Request) -> Response:
    if not oauth_challenge_enabled():
        return _disabled()
    # 中台独立 AS：把发现文档原样转到 UPSTREAM（客户端常在 MCP 主机探 AS）
    if uses_external_authorization_server(request):
        return await _proxy_external_as(request, "/.well-known/oauth-authorization-server")
    if not oauth_enabled():
        return _disabled()
    issuer = resolve_service_public_base(request)
    return JSONResponse(_authorization_server_metadata(issuer))


async def openid_configuration(request: Request) -> Response:
    """OIDC 发现文档。WorkBuddy 等会在 MCP 路径下探 /.well-known/openid-configuration。"""
    if not oauth_challenge_enabled():
        return _disabled()
    if uses_external_authorization_server(request):
        return await _proxy_external_as(request, "/.well-known/openid-configuration")
    if not oauth_enabled():
        return _disabled()
    issuer = resolve_service_public_base(request)
    return JSONResponse(_authorization_server_metadata(issuer))


async def register_client(request: Request) -> Response:
    if uses_external_authorization_server(request):
        # Cherry Studio 等对 MCP URL 主机直接 POST /oauth/register，需代理到中台
        return await _proxy_external_as(request, "/oauth/register")
    if not oauth_enabled():
        return _disabled()
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    redirect_uris = body.get("redirect_uris") or []
    if not isinstance(redirect_uris, list) or not redirect_uris:
        return JSONResponse(
            {"error": "invalid_client_metadata", "error_description": "redirect_uris required"},
            status_code=400,
        )
    for uri in redirect_uris:
        if not isinstance(uri, str) or not _validate_redirect_uri(uri):
            return JSONResponse(
                {
                    "error": "invalid_redirect_uri",
                    "error_description": _redirect_uri_error_description(),
                },
                status_code=400,
            )
    client_id = str(uuid.uuid4())
    if _put_pending_client(
        client_id=client_id,
        redirect_uris=list(redirect_uris),
        client_name=str(body.get("client_name") or "mcp-client"),
    ) is None:
        return _client_capacity_error(as_html=False)
    return JSONResponse(
        {
            "client_id": client_id,
            "client_id_issued_at": int(time.time()),
            "redirect_uris": redirect_uris,
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        },
        status_code=201,
    )





async def authorize(request: Request) -> Response:
    if uses_external_authorization_server(request):
        if request.method == "GET":
            return _redirect_external_authorize(request)
        return await _proxy_external_as(request, "/oauth/authorize")
    if not oauth_enabled():
        return _disabled()

    if request.method == "GET":
        q = request.query_params
        client_id = q.get("client_id") or ""
        redirect_uri = q.get("redirect_uri") or ""
        state = q.get("state") or ""
        code_challenge = q.get("code_challenge") or ""
        method = q.get("code_challenge_method") or "S256"
        scope = q.get("scope") or "mcp"
        response_type = q.get("response_type") or "code"

        err = ""
        if response_type != "code":
            err = "仅支持 response_type=code"
        elif not client_id:
            err = "缺少 client_id"
        elif client_id not in _clients:
            # 允许未注册 client（部分客户端跳过 DCR）；仍校验 redirect
            if (
                _put_pending_client(
                    client_id=client_id,
                    redirect_uris=[redirect_uri] if redirect_uri else [],
                    client_name="dynamic",
                )
                is None
            ):
                return _client_capacity_error(as_html=True)
        else:
            _prune_pending_clients()
            if client_id not in _clients:
                # 刚被超时清理
                if (
                    _put_pending_client(
                        client_id=client_id,
                        redirect_uris=[redirect_uri] if redirect_uri else [],
                        client_name="dynamic",
                    )
                    is None
                ):
                    return _client_capacity_error(as_html=True)
            else:
                _touch_client(client_id)
        if not err and not _validate_redirect_uri(redirect_uri):
            err = "redirect_uri 不符合白名单（本机 /oauth/callback|/callback，或 Cursor 回调）"
        if not err and method.upper() != "S256":
            err = "仅支持 code_challenge_method=S256"
        if not err and not code_challenge:
            err = "缺少 code_challenge（PKCE）"

        if err and not _validate_redirect_uri(redirect_uri):
            return HTMLResponse(_consent_html(error=err), status_code=400)

        return HTMLResponse(
            _consent_html(
                error=err,
                client_id=client_id,
                redirect_uri=redirect_uri,
                state=state,
                code_challenge=code_challenge,
                code_challenge_method=method,
                scope=scope,
            )
        )

    # POST
    ip = _client_ip(request)
    rate_key = f"authorize:{ip}"
    if not _rate_allow(rate_key):
        return HTMLResponse(
            _consent_html(error=f"尝试过于频繁，请 {_rate_window_sec()} 秒后再试"),
            status_code=429,
        )

    form = await request.form()
    client_id = str(form.get("client_id") or "")
    redirect_uri = str(form.get("redirect_uri") or "")
    state = str(form.get("state") or "")
    code_challenge = str(form.get("code_challenge") or "")
    method = str(form.get("code_challenge_method") or "S256")
    scope = str(form.get("scope") or "mcp")
    ak = str(form.get("access_key") or "").strip()
    sk = str(form.get("secret_key") or "").strip()
    captcha_id = str(form.get("captcha_id") or "")
    captcha_answer = str(form.get("captcha_answer") or "")

    def _redisplay(msg: str, *, status: int = 400) -> HTMLResponse:
        return HTMLResponse(
            _consent_html(
                error=msg,
                client_id=client_id,
                redirect_uri=redirect_uri,
                state=state,
                code_challenge=code_challenge,
                code_challenge_method=method,
                scope=scope,
            ),
            status_code=status,
        )

    if not _validate_redirect_uri(redirect_uri):
        return _redisplay("非法 redirect_uri")
    if captcha_enabled() and not _verify_captcha(captcha_id, captcha_answer):
        return _redisplay("验证码错误或已过期，请重试")
    if not ak or not sk:
        return _redisplay("请填写 Access Key 与 Secret Key")

    token, uid, tenantid, productcode = _login(ak, sk)
    if not token:
        return _redisplay(f"鉴权失败，请检查 AK/SK（loginV2: {AUTHORIZATION_URL}）")

    if client_id and client_id not in _clients:
        if (
            _put_pending_client(
                client_id=client_id,
                redirect_uris=[redirect_uri],
                client_name="dynamic",
            )
            is None
        ):
            return _client_capacity_error(as_html=True)
    elif client_id in _clients:
        uris = _clients[client_id].setdefault("redirect_uris", [])
        if redirect_uri not in uris:
            uris.append(redirect_uri)

    code = secrets.token_urlsafe(32)
    _auth_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": method.upper(),
        "scope": scope,
        "cred": _encrypt_creds(ak, sk),
        "uid": uid,
        "tenantid": tenantid,
        "productcode": productcode,
        "exp": time.time() + CODE_TTL_SEC,
    }
    _mark_client_completed(client_id)
    params = {"code": code}
    if state:
        params["state"] = state
    sep = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(f"{redirect_uri}{sep}{urlencode(params)}", status_code=302)


def _issue_tokens(
    *,
    client_id: str,
    cred: str,
    uid: Optional[str],
    tenantid: Optional[str],
    productcode: Optional[str],
    scope: str,
    issuer: Optional[str] = None,
) -> Dict[str, Any]:
    now = int(time.time())
    iss = (issuer or resolve_service_public_base()).rstrip("/")
    access = jwt.encode(
        {
            "iss": iss,
            "aud": JWT_ISS_CLAIM,
            "sub": uid or client_id,
            "typ": "access",
            "cid": client_id,
            "cred": cred,
            "uid": uid,
            "tenantid": tenantid,
            "productcode": productcode,
            "scope": scope,
            "iat": now,
            "exp": now + ACCESS_TTL_SEC,
        },
        _jwt_secret(),
        algorithm=JWT_ALG,
    )
    refresh = jwt.encode(
        {
            "iss": iss,
            "aud": JWT_ISS_CLAIM,
            "sub": uid or client_id,
            "typ": "refresh",
            "cid": client_id,
            "cred": cred,
            "uid": uid,
            "tenantid": tenantid,
            "productcode": productcode,
            "scope": scope,
            "iat": now,
            "exp": now + REFRESH_TTL_SEC,
        },
        _jwt_secret(),
        algorithm=JWT_ALG,
    )
    return {
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": ACCESS_TTL_SEC,
        "refresh_token": refresh,
        "scope": scope,
    }


async def token(request: Request) -> Response:
    if uses_external_authorization_server(request):
        return await _proxy_external_as(request, "/oauth/token")
    if not oauth_enabled():
        return _disabled()

    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
    else:
        form = await request.form()
        data = {k: str(v) for k, v in form.items()}

    grant = (data.get("grant_type") or "").strip()
    client_id = (data.get("client_id") or "").strip()

    if grant == "authorization_code":
        code = (data.get("code") or "").strip()
        redirect_uri = (data.get("redirect_uri") or "").strip()
        verifier = (data.get("code_verifier") or "").strip()
        entry = _auth_codes.pop(code, None)
        if not entry or entry["exp"] < time.time():
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "code invalid or expired"},
                status_code=400,
            )
        if entry["client_id"] and client_id and entry["client_id"] != client_id:
            return JSONResponse({"error": "invalid_grant", "error_description": "client_id mismatch"}, status_code=400)
        if entry["redirect_uri"] != redirect_uri:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "redirect_uri mismatch"},
                status_code=400,
            )
        if entry["code_challenge_method"] != "S256":
            return JSONResponse({"error": "invalid_grant", "error_description": "unsupported PKCE"}, status_code=400)
        if _pkce_s256(verifier) != entry["code_challenge"]:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "code_verifier mismatch"},
                status_code=400,
            )
        return JSONResponse(
            _issue_tokens(
                client_id=entry["client_id"] or client_id,
                cred=entry["cred"],
                uid=entry.get("uid"),
                tenantid=entry.get("tenantid"),
                productcode=entry.get("productcode"),
                scope=entry.get("scope") or "mcp",
                issuer=resolve_service_public_base(request),
            )
        )

    if grant == "refresh_token":
        refresh = (data.get("refresh_token") or "").strip()
        try:
            claims = _decode_mcp_jwt(refresh)
        except jwt.PyJWTError:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "refresh_token invalid or expired"},
                status_code=400,
            )
        if claims.get("typ") != "refresh":
            return JSONResponse({"error": "invalid_grant"}, status_code=400)
        cred = claims.get("cred")
        if not isinstance(cred, str) or not _decrypt_creds(cred):
            return JSONResponse({"error": "invalid_grant", "error_description": "credentials lost"}, status_code=400)
        # 可选：refresh 时再校验 loginV2
        pair = _decrypt_creds(cred)
        assert pair is not None
        biz, uid, tenantid, productcode = _login(pair[0], pair[1])
        if not biz:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "credentials rejected by loginV2"},
                status_code=400,
            )
        return JSONResponse(
            _issue_tokens(
                client_id=str(claims.get("cid") or client_id),
                cred=cred,
                uid=uid or claims.get("uid"),
                tenantid=tenantid or claims.get("tenantid"),
                productcode=productcode or claims.get("productcode"),
                scope=str(claims.get("scope") or "mcp"),
                issuer=resolve_service_public_base(request),
            )
        )

    return JSONResponse(
        {"error": "unsupported_grant_type", "error_description": "use authorization_code or refresh_token"},
        status_code=400,
    )


async def health(request: Request) -> Response:
    oauth_on = oauth_challenge_enabled()
    external = uses_external_authorization_server(request)
    return JSONResponse(
        {
            "status": "ok",
            "layout": "unified",
            "oauth": oauth_on,
            "oauth_local_as": oauth_enabled() and not external,
            "oauth_external_as": external,
            "resource": public_resource_url(request) if oauth_on else None,
            "issuer": resolve_public_base(request) if oauth_on else None,
            "upstream": resolve_oauth_upstream() if external else None,
        }
    )


def oauth_routes() -> List[Route]:
    """挂载 OAuth + health。规范路径优先，并保留 /authorize|/token|/register 别名。"""
    return [
        Route("/health", endpoint=health, methods=["GET"]),
        Route("/.well-known/oauth-protected-resource", endpoint=oauth_protected_resource, methods=["GET"]),
        Route("/.well-known/oauth-authorization-server", endpoint=oauth_authorization_server, methods=["GET"]),
        Route("/.well-known/openid-configuration", endpoint=openid_configuration, methods=["GET"]),
        Route("/oauth/register", endpoint=register_client, methods=["POST"]),
        Route("/register", endpoint=register_client, methods=["POST"]),
        Route("/oauth/authorize", endpoint=authorize, methods=["GET", "POST"]),
        Route("/authorize", endpoint=authorize, methods=["GET", "POST"]),
        Route("/oauth/token", endpoint=token, methods=["POST"]),
        Route("/token", endpoint=token, methods=["POST"]),
    ]

