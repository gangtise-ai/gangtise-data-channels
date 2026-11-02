# HTTP / SSE

**简体中文** | [English](http-sse.md)

远程地址由本仓库提供。HTTP：`https://openapi.gangtise.com/application/mcp/` · SSE：`https://openapi.gangtise.com/application/mcp/sse`。进程内默认挂在根路径 `POST /`；网关可加前缀（如 `/application/mcp`）。用 `MCP_PATH` 改进程内挂载路径。

---

## 传输

| 模式 | 端点 |
|------|------|
| streamable-http | 线上：`https://openapi.gangtise.com/application/mcp/` · 进程内：`POST /`（`MCP_PATH`） |
| SSE | 线上：`https://openapi.gangtise.com/application/mcp/sse` · 进程内：`GET /sse` + `POST /messages/` |

SSE 需要 `MCP_TRANSPORT=sse` 或 `both`。经网关剥离前缀时，服务端下发相对路径 `messages/?session_id=…`，客户端会把它解析到与 `/sse` 相同的前缀下。

健康检查：`GET /health`。

`MCP_REQUIRE_AUTH=true` 时，访问 MCP 路径却没有鉴权会返回 **401**。响应回传 `X-DashScope-Request-ID`。

---

<details open>
<summary><b>鉴权</b></summary>

两种方式可同时使用。远程接入优先传 AK/SK。

解析顺序：**Authorization → AK/SK**（含 `X-GTS-Credentials`）。

### 1. AK/SK（推荐）

```http
accessKey: <ak>
secretKey: <sk>
```

或：

```http
X-GTS-Credentials: {"accessKey":"<ak>","secretKey":"<sk>"}
```

stdio：`GTS_ACCESS_KEY` + `GTS_SECRET_KEY`，或本地 `~/.config/gangtise/authorization`。

### 2. Authorization

```http
Authorization: Bearer <token>
```

原样透传下游。stdio：`GTS_AUTHORIZATION`，或同一本地凭证文件。

</details>

<details open>
<summary><b>客户端示例</b>（`~/.cursor/mcp.json`）</summary>

`type` 要和 URL 一致：HTTP 基址用 `streamableHttp`，`/sse` 用 `sse`。不要把 `streamableHttp` 指到 `/sse`。

**Streamable HTTP + AK/SK**

```json
{
  "mcpServers": {
    "gangtise": {
      "type": "streamableHttp",
      "url": "https://openapi.gangtise.com/application/mcp/",
      "headers": {
        "accessKey": "<ak>",
        "secretKey": "<sk>"
      }
    }
  }
}
```

**SSE + AK/SK**

```json
{
  "mcpServers": {
    "gangtise-sse": {
      "type": "sse",
      "url": "https://openapi.gangtise.com/application/mcp/sse",
      "headers": {
        "accessKey": "<ak>",
        "secretKey": "<sk>"
      }
    }
  }
}
```

`X-GTS-Credentials`（`type` / `url` 同上）：

```json
{
  "mcpServers": {
    "gangtise": {
      "type": "streamableHttp",
      "url": "https://openapi.gangtise.com/application/mcp/",
      "headers": {
        "X-GTS-Credentials": "{\"accessKey\":\"<ak>\",\"secretKey\":\"<sk>\"}"
      }
    }
  }
}
```

Bearer：

```json
{
  "mcpServers": {
    "gangtise": {
      "type": "streamableHttp",
      "url": "https://openapi.gangtise.com/application/mcp/",
      "headers": {
        "Authorization": "Bearer <token>"
      }
    }
  }
}
```

</details>

---

[Docker 部署](docker-deploy.cn.md) · [CLI](cli.cn.md) · [总览](../README.cn.md)
