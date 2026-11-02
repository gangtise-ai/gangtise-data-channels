# Gangtise MCP

单一 MCP 包：stdio（`gangtise-mcp`）与 HTTP/SSE（`gangtise-mcp-api`）。
运行时只使用 `mcp/src` + `mcp/src/_generated`（core 与 handlers 均由 `scripts/generate.py` 写入）。不要把仓库 `core/` 或 `skills/` 加进 PYTHONPATH。

改 `core/` 或 `skills/openapi` 后先在仓库根执行 `python3 scripts/generate.py`。

```bash
cd mcp && uv sync
uv run gangtise-mcp          # stdio
uv run gangtise-mcp-api      # HTTP，默认 0.0.0.0:8000
```

Docker（仓库根，且已 generate）：`docker build -t gangtise-mcp -f mcp/Dockerfile .`
自有集群启动脚本（`local_start.sh`、`gangtise-mcp.yaml` 等）在 `.gitignore` 中，不进开源仓。
