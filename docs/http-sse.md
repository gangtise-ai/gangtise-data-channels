# HTTP / SSE

[简体中文](http-sse.cn.md) | **English**

The remote endpoints are served by this repository. HTTP: `https://openapi.gangtise.com/application/mcp/` · SSE: `https://openapi.gangtise.com/application/mcp/sse`. In-process default is `POST /`; a gateway may add a prefix such as `/application/mcp`. Set `MCP_PATH` to change the in-process mount.

---

## Transport

| Mode | Endpoint |
|------|----------|
| streamable-http | Production: `https://openapi.gangtise.com/application/mcp/` · In-process: `POST /` (`MCP_PATH`) |
| SSE | Production: `https://openapi.gangtise.com/application/mcp/sse` · In-process: `GET /sse` + `POST /messages/` |

SSE needs `MCP_TRANSPORT=sse` or `both`. Behind a path-stripping gateway the server advertises a relative `messages/?session_id=…`, which clients resolve under the same prefix as `/sse`.

Health: `GET /health`.

With `MCP_REQUIRE_AUTH=true`, an MCP path without credentials returns **401**. Responses echo `X-DashScope-Request-ID`.

---

<details open>
<summary><b>Auth</b></summary>

Both methods can be used together. For remote clients, prefer AK/SK.

Resolution order: **Authorization → AK/SK** (including `X-GTS-Credentials`).

### 1. AK/SK (recommended)

```http
accessKey: <ak>
secretKey: <sk>
```

Or:

```http
X-GTS-Credentials: {"accessKey":"<ak>","secretKey":"<sk>"}
```

stdio: `GTS_ACCESS_KEY` + `GTS_SECRET_KEY`, or `~/.config/gangtise/authorization`.

### 2. Authorization

```http
Authorization: Bearer <token>
```

Passed through downstream. stdio: `GTS_AUTHORIZATION`, or the same local credentials file.

</details>

<details open>
<summary><b>Client example</b> (`~/.cursor/mcp.json`)</summary>

Match `type` to the URL: `streamableHttp` for the HTTP base, `sse` for `/sse`. Do not point `streamableHttp` at `/sse`.

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

`X-GTS-Credentials` (same `type` / `url`):

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

Bearer:

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

[Docker](docker-deploy.md) · [CLI](cli.md) · [Overview](../README.md)
