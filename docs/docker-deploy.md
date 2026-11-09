# Docker deploy

[简体中文](docker-deploy.cn.md) | **English**

The image contains this repo's `mcp/` only (`mcp/Dockerfile`). Default transport is HTTP (`MCP_TRANSPORT=http`) mounted at `/`. The public gateway prefix is what turns that into `https://openapi.gangtise.com/application/mcp/`. Protocol and auth: [http-sse.md](http-sse.md).

| Piece | Role | Notes |
|-------|------|--------|
| **Base image** `BASE_IMAGE` | Official `python:3.11.9` | If Docker Hub is unreachable, retag a local image and pass `--build-arg BASE_IMAGE=...` |
| **pip index** | Install Python dependencies | Examples use the Tsinghua mirror |

---

<details open>
<summary><b>Build and run</b></summary>

From the repository root:

```bash
docker build -t gangtise-mcp -f mcp/Dockerfile \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  --build-arg PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
  .

docker run -d --name gangtise-mcp -p 8000:8000 gangtise-mcp

curl -sS http://127.0.0.1:8000/health
```

Point the client at `http://127.0.0.1:8000/` with `accessKey` / `secretKey`, or `Authorization: Bearer <token>`.

</details>

<details>
<summary><b>Common environment variables</b></summary>

| Variable | Default | Notes |
|----------|---------|--------|
| `GANGTISE_AUTH_DOMAIN` | `https://openapi.gangtise.com/application/auth` | loginV2 base; requests go to `{GANGTISE_AUTH_DOMAIN}/oauth/open/loginV2` |
| `MCP_TRANSPORT` | `http` | `http` / `sse` / `both` |
| `MCP_PATH` | `/` | In-process MCP mount |
| `SUBPATHS` | empty | Comma-separated source prefixes. `doubao,ali` makes `/open-mcp/doubao/` hit the same server as `/open-mcp/` |
| `SUBPATHS_MODE` | empty | Per-subpath exposure, e.g. `doubao:leaf;progressive:progressive`. Unlisted subpaths default to leaf; main path still uses `MCP_TOOL_EXPOSURE` |
| `MCP_PROGRESSIVE_SUBPATH` | empty | Compat shorthand: add that name to `SUBPATHS` and mark it progressive (same as `{name}:progressive` in `SUBPATHS_MODE`) |
| `MCP_REQUIRE_AUTH` | `true` | HTTP 401 when the MCP path has neither Authorization nor AK/SK |
| `MCP_TOOL_BLACKLIST` | empty | Tool/skill blacklist. Main segment applies to every entry; append per subpath with `;subpath:names`. Example: `A,B;doubao:C;progressive:D,E` → main blocks A,B; doubao blocks A,B,C; progressive blocks A,B,D,E |
| `MCP_HOST` / `MCP_PORT` | `0.0.0.0` / `8000` | Bind address |
| `GTS_JWT_SECRET` | empty | Enables the local OAuth authorization server. Without it, `/oauth/*` returns 503; AK/SK and Authorization still work |
| `GTS_OAUTH_RESOURCE` | empty (this service) | OAuth `resource` base URL |
| `GTS_OAUTH_ISSUER` | empty (this service) | Public issuer in `authorization_servers` and browser authorize redirects. When using an external AS, it must match that AS metadata `issuer` |
| `GTS_OAUTH_UPSTREAM` | `https://auth.gangtise.com` | Upstream base for proxying `/oauth/*` and `/.well-known/openid-configuration` under the MCP path when using an external AS. In-cluster example: `http://workbuddy-connector-server.platform-business:15684` |
| `GTS_OAUTH_SCOPES` | `mcp` | `scopes_supported` on the protected-resource metadata. Match the external AS, e.g. `mcp.read mcp.write` |
| `GTS_ACCESS_KEY` / `GTS_SECRET_KEY` | empty | Process-level AK/SK. Remote clients usually send headers per request instead |
| `OBS_*` | empty | Optional attachment offload: `OBS_ACCESS_KEY` / `OBS_SECRET_KEY` / `OBS_ENDPOINT` / `OBS_BUCKET` / `OBS_PATH` |
| `MCP_ATTACH_OBS_ALWAYS` | `false` | When `true`, upload every attachment to OBS and return a link in the text |
| `OBS_EXPIRE_DAYS` | `1` | How many days an OBS object is kept |

Clients that do not read embedded MCP resources (WorkBuddy, for example) should set `MCP_ATTACH_OBS_ALWAYS=true`. Install the OBS SDK at build time with `--build-arg INSTALL_OBS=1`.

</details>

---

[HTTP / SSE](http-sse.md) · [CLI](cli.md) · [Overview](../README.md)
