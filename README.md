<div align="center">

# Gangtise MCP

[简体中文](README.cn.md) | **English**

Remote service: [`https://openapi.gangtise.com/application/mcp/`](https://openapi.gangtise.com/application/mcp/) (served by this repository).

[Get credentials](https://open-platform.gangtise.com/) ·
[HTTP / SSE](docs/http-sse.md) ·
[CLI](docs/cli.md) ·
[Docker](docs/docker-deploy.md)

</div>

---

## Connect

1. Create an account on the [open platform](https://open-platform.gangtise.com/) and copy **Access Key / Secret Key** from account settings.
2. Pick a connection mode. For remote use, point the client at the HTTP URL below and send AK/SK headers.

| Mode | Notes |
|------|--------|
| **Remote HTTP (recommended)** | `https://openapi.gangtise.com/application/mcp/`, `streamableHttp`, headers `accessKey` / `secretKey` |
| **Remote SSE** | `https://openapi.gangtise.com/application/mcp/sse`, `type` `sse` |
| **Local stdio** | `uvx` runs `gangtise-mcp`; env `GTS_ACCESS_KEY` / `GTS_SECRET_KEY` |
| **CLI** | `uvx` runs `gangtise` (see [docs/cli.md](docs/cli.md)) |

Examples below use GitHub: [`https://github.com/gangtise-ai/gangtise-data-channels`](https://github.com/gangtise-ai/gangtise-data-channels). Chinese docs use Gitee — see [README.cn.md](README.cn.md).

Two auth methods can be used together. Server order: **Authorization → AK/SK** (`accessKey` / `secretKey`, or `X-GTS-Credentials`).

```http
accessKey: <ak>
secretKey: <sk>
```

```http
Authorization: Bearer <token>
```

---

## Install by platform

> On clients with an agent, paste the JSON below and ask it to install. You can also write the same JSON into the client config file.

<details open>
<summary><b>Cursor</b></summary>

Remote HTTP (recommended). Write `~/.cursor/mcp.json` or project `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "gangtise": {
      "type": "streamableHttp",
      "url": "https://openapi.gangtise.com/application/mcp/",
      "headers": {
        "accessKey": "YOUR_ACCESS_KEY",
        "secretKey": "YOUR_SECRET_KEY"
      }
    }
  }
}
```

Open **Cursor → Settings → Tools & MCP** and enable `gangtise`. `type` must be `streamableHttp`. Do not point that type at `/sse`.

Local stdio (requires [uv](https://docs.astral.sh/uv/)):

```json
{
  "mcpServers": {
    "gangtise": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/gangtise-ai/gangtise-data-channels#subdirectory=mcp",
        "gangtise-mcp"
      ],
      "env": {
        "GTS_ACCESS_KEY": "YOUR_ACCESS_KEY",
        "GTS_SECRET_KEY": "YOUR_SECRET_KEY"
      }
    }
  }
}
```

</details>

<details>
<summary><b>WorkBuddy</b></summary>

Guide: [WorkBuddy MCP](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/MCP-Guide). Use the same remote HTTP endpoint as Cursor: `https://openapi.gangtise.com/application/mcp/`, `streamableHttp`, AK/SK headers. After install, trust and enable it under **Connectors → My MCP**.

</details>

<details>
<summary><b>Claude Desktop</b></summary>

Edit `claude_desktop_config.json` with the same stdio JSON as Cursor (`mcpServers.gangtise`). Requires [uv](https://docs.astral.sh/uv/).

</details>

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add gangtise -- uvx \
  --from "git+https://github.com/gangtise-ai/gangtise-data-channels#subdirectory=mcp" \
  gangtise-mcp
```

Set `GTS_ACCESS_KEY` / `GTS_SECRET_KEY` on that MCP entry. Remote HTTP: [docs/http-sse.md](docs/http-sse.md).

</details>

<details>
<summary><b>VS Code</b></summary>

Workspace `.vscode/mcp.json`:

```json
{
  "servers": {
    "gangtise": {
      "type": "http",
      "url": "https://openapi.gangtise.com/application/mcp/",
      "headers": {
        "accessKey": "YOUR_ACCESS_KEY",
        "secretKey": "YOUR_SECRET_KEY"
      }
    }
  }
}
```

</details>

<details>
<summary><b>Remote HTTP / SSE</b></summary>

```
HTTP  https://openapi.gangtise.com/application/mcp/
SSE   https://openapi.gangtise.com/application/mcp/sse
```

SSE `type`, `X-GTS-Credentials`, and header details: [docs/http-sse.md](docs/http-sse.md). Self-host: [docs/docker-deploy.md](docs/docker-deploy.md).

</details>

---

<details>
<summary><b>Run from source</b></summary>

```bash
# stdio
cd mcp && uv sync
uv run gangtise-mcp

# HTTP, default 0.0.0.0:8000
uv run gangtise-mcp-api

# CLI
cd ../cli && uv sync
uv run gangtise list
```

After editing `core/` or `skills/openapi/`, run `python3 scripts/generate.py` at the repo root before the commands above.

</details>

---

Chinese: [README.cn.md](README.cn.md).

## License

[MIT](LICENSE) © 2026 Gangtise
