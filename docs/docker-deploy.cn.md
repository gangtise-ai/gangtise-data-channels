# Docker 部署

**简体中文** | [English](docker-deploy.md)

镜像只包含本仓库的 `mcp/`（`mcp/Dockerfile`）。默认 HTTP：`MCP_TRANSPORT=http`，进程内挂在 `/`。线上网关再加上前缀后就是 `https://openapi.gangtise.com/application/mcp/`。协议与鉴权见 [http-sse.cn.md](http-sse.cn.md)。

| 类型 | 用途 | 说明 |
|------|------|------|
| **基础镜像** `BASE_IMAGE` | 官方 `python:3.11.9` | 拉不到 Docker Hub 时，在本机打好标签再传 `--build-arg BASE_IMAGE=...` |
| **pip 索引** | 安装 Python 依赖 | 示例使用清华源 |

---

<details open>
<summary><b>构建与运行</b></summary>

在仓库根目录：

```bash
docker build -t gangtise-mcp -f mcp/Dockerfile \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  --build-arg PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
  .

docker run -d --name gangtise-mcp -p 8000:8000 gangtise-mcp

curl -sS http://127.0.0.1:8000/health
```

客户端连接 `http://127.0.0.1:8000/`，请求头带 `accessKey` / `secretKey`，或 `Authorization: Bearer <token>`。

</details>

<details>
<summary><b>常用环境变量</b></summary>

| 变量 | 默认 | 说明 |
|------|------|------|
| `GANGTISE_AUTH_DOMAIN` | `https://openapi.gangtise.com/application/auth` | loginV2 基址；实际请求 `{GANGTISE_AUTH_DOMAIN}/oauth/open/loginV2` |
| `MCP_TRANSPORT` | `http` | `http` / `sse` / `both` |
| `MCP_PATH` | `/` | 进程内 MCP 挂载路径 |
| `SUBPATHS` | 空 | 来源子路径，逗号分隔。例如 `doubao,ali` 时 `/open-mcp/doubao/` 与 `/open-mcp/` 落到同一服务 |
| `SUBPATHS_MODE` | 空 | 子路径暴露模式，如 `doubao:leaf;progressive:progressive`。未声明的子路径默认 leaf；主路径仍按 `MCP_TOOL_EXPOSURE` |
| `MCP_PROGRESSIVE_SUBPATH` | 空 | 兼容简写：并入 `SUBPATHS` 且该入口为 progressive（等同 `SUBPATHS_MODE` 中 `{name}:progressive`） |
| `MCP_REQUIRE_AUTH` | `true` | MCP 路径没有 Authorization 或 AK/SK 时返回 401 |
| `MCP_TOOL_BLACKLIST` | 空 | 工具/skill 黑名单。主段对所有入口生效；可用 `;子路径:名` 追加。例：`A,B;doubao:C;progressive:D,E` → 主路径屏蔽 A,B；doubao 屏蔽 A,B,C；progressive 屏蔽 A,B,D,E |
| `MCP_HOST` / `MCP_PORT` | `0.0.0.0` / `8000` | 监听地址 |
| `GTS_JWT_SECRET` | 空 | 设置后启用本机 OAuth。未设置时 `/oauth/*` 返回 503，AK/SK 与 Authorization 仍可用 |
| `GTS_OAUTH_RESOURCE` | 空（默认本服务） | OAuth `resource` 基址 |
| `GTS_OAUTH_ISSUER` | 空（回退本服务） | `authorization_servers` 的公网 issuer；浏览器授权 302 也用它。指向外部 AS 时须与其 metadata `issuer` 一致 |
| `GTS_OAUTH_UPSTREAM` | `https://auth.gangtise.com` | 外部 AS 时，MCP 路径下 `/oauth/*`、`/.well-known/openid-configuration` 等转发基址。集群内可填内网，例如 `http://workbuddy-connector-server.platform-business:15684` |
| `GTS_OAUTH_SCOPES` | `mcp` | 保护资源 metadata 的 `scopes_supported`。使用外部授权服务时须与其 scope 一致，例如 `mcp.read mcp.write` |
| `GTS_ACCESS_KEY` / `GTS_SECRET_KEY` | 空 | 进程级 AK/SK。远程客户端更常见的是每个请求自己带请求头 |
| `OBS_*` | 空 | 可选附件外置：`OBS_ACCESS_KEY` / `OBS_SECRET_KEY` / `OBS_ENDPOINT` / `OBS_BUCKET` / `OBS_PATH` |
| `MCP_ATTACH_OBS_ALWAYS` | `false` | `true` 时附件一律上传 OBS，正文只返回链接 |
| `OBS_EXPIRE_DAYS` | `1` | OBS 对象保留天数 |

不解析 MCP 内嵌附件的客户端（如 WorkBuddy）请设 `MCP_ATTACH_OBS_ALWAYS=true`。构建时安装 OBS SDK：`--build-arg INSTALL_OBS=1`。

</details>

---

[HTTP / SSE](http-sse.cn.md) · [CLI](cli.cn.md) · [总览](../README.cn.md)
