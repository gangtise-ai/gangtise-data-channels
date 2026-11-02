<div align="center">

# Gangtise MCP

**简体中文** | [English](README.md)

远程服务：[`https://openapi.gangtise.com/application/mcp/`](https://openapi.gangtise.com/application/mcp/)（由本仓库提供）。

[账号申请](https://open-platform.gangtise.com/) ·
[HTTP / SSE](docs/http-sse.cn.md) ·
[CLI](docs/cli.cn.md) ·
[Docker](docs/docker-deploy.cn.md)

</div>

---

## 对接

1. 在 [开放平台](https://open-platform.gangtise.com/) 申请账号，于「我的账号 → 账号列表」获取 **Access Key / Secret Key**。
2. 选一种连接方式。日常远程接入用下面的 HTTP 地址，请求头带 AK/SK。

| 方式 | 说明 |
|------|------|
| **远程 HTTP（推荐）** | `https://openapi.gangtise.com/application/mcp/`，`streamableHttp`，请求头 `accessKey` / `secretKey` |
| **远程 SSE** | `https://openapi.gangtise.com/application/mcp/sse`，`type` 用 `sse` |
| **本地 stdio** | `uvx` 拉起 `gangtise-mcp`，环境变量 `GTS_ACCESS_KEY` / `GTS_SECRET_KEY` |
| **命令行 CLI** | `uvx` 拉起 `gangtise`（见 [docs/cli.cn.md](docs/cli.cn.md)） |

中文示例使用 Gitee：[`https://gitee.com/gangtise/gangtise-data-channels`](https://gitee.com/gangtise/gangtise-data-channels)。英文示例见 [README.md](README.md)（GitHub）。

鉴权两种，可同时存在。服务端优先级：**Authorization → AK/SK**（请求头 `accessKey` / `secretKey`，或 `X-GTS-Credentials`）。

```http
accessKey: <ak>
secretKey: <sk>
```

```http
Authorization: Bearer <token>
```

---

## 按平台安装

> 带智能体的客户端可以把下方 JSON 发给智能体安装，也可以自己写入对应配置文件。

<details open>
<summary><b>Cursor</b></summary>

远程 HTTP（推荐）。写入 `~/.cursor/mcp.json` 或项目 `.cursor/mcp.json`：

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

打开 **Cursor → Settings → Tools & MCP**，确认 `gangtise` 已开启。`type` 必须是 `streamableHttp`，不要把该类型指到 `/sse`。

本地 stdio（需已安装 [uv](https://docs.astral.sh/uv/)）：

```json
{
  "mcpServers": {
    "gangtise": {
      "command": "uvx",
      "args": [
        "--default-index",
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        "--from",
        "git+https://gitee.com/gangtise/gangtise-data-channels#subdirectory=mcp",
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
<summary><b>WorkBuddy（腾讯云代码助手）</b></summary>

官方说明见 [WorkBuddy MCP 指南](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/MCP-Guide)。远程 HTTP 与 Cursor 相同：`https://openapi.gangtise.com/application/mcp/`，`streamableHttp`，请求头带 AK/SK。安装后在 **连接器 → 我的 MCP** 中信任并开启。

</details>

<details>
<summary><b>Claude Desktop</b></summary>

编辑 `claude_desktop_config.json`，内容与 Cursor 的 stdio JSON 相同（`mcpServers.gangtise`）。需已安装 [uv](https://docs.astral.sh/uv/)。

</details>

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add gangtise -- uvx \
  --default-index https://pypi.tuna.tsinghua.edu.cn/simple \
  --from "git+https://gitee.com/gangtise/gangtise-data-channels#subdirectory=mcp" \
  gangtise-mcp
```

在对应 MCP 配置里设置 `GTS_ACCESS_KEY` / `GTS_SECRET_KEY`。远程 HTTP 见 [docs/http-sse.cn.md](docs/http-sse.cn.md)。

</details>

<details>
<summary><b>VS Code</b></summary>

工作区 `.vscode/mcp.json`：

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
<summary><b>远程 HTTP / SSE</b></summary>

```
HTTP  https://openapi.gangtise.com/application/mcp/
SSE   https://openapi.gangtise.com/application/mcp/sse
```

协议、SSE 的 `type`、以及 `X-GTS-Credentials` 写法见 [docs/http-sse.cn.md](docs/http-sse.cn.md)。自建见 [docs/docker-deploy.cn.md](docs/docker-deploy.cn.md)。

</details>

---

<details>
<summary><b>从源码运行</b></summary>

```bash
# stdio
cd mcp && uv sync --default-index https://pypi.tuna.tsinghua.edu.cn/simple
uv run gangtise-mcp

# HTTP，默认 0.0.0.0:8000
uv run gangtise-mcp-api

# CLI
cd ../cli && uv sync --default-index https://pypi.tuna.tsinghua.edu.cn/simple
uv run gangtise list
```

改 `core/` 或 `skills/openapi/` 后，先在仓库根执行 `python3 scripts/generate.py`，再运行上面的命令。

</details>

---

English：[README.md](README.md)。

## 许可证

[MIT](LICENSE) © 2026 Gangtise
