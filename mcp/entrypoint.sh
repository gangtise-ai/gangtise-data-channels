#!/usr/bin/env bash
# Docker 入口：stdio → gangtise-mcp；HTTP/SSE → gangtise-mcp-api。
# 只使用 /opt/mcp（来自 mcp/ 包），不挂仓库 core/ 或 skills/。
set -euo pipefail

MCP_HOST="${MCP_HOST:-0.0.0.0}"
MCP_PORT="${MCP_PORT:-8000}"
MCP_TRANSPORT="${MCP_TRANSPORT:-http}"
export GTS_SAVE_FILE="${GTS_SAVE_FILE:-False}"
export GTS_MCP_ROOT="${GTS_MCP_ROOT:-/opt/mcp}"
export MCP_LAYOUT=unified
export MCP_REQUIRE_AUTH="${MCP_REQUIRE_AUTH:-true}"
export MCP_PATH="${MCP_PATH:-/}"
export MCP_STATELESS="${MCP_STATELESS:-true}"
export MCP_JSON_RESPONSE="${MCP_JSON_RESPONSE:-true}"
export SUBPATHS="${SUBPATHS:-}"
export SUBPATHS_MODE="${SUBPATHS_MODE:-}"
export MCP_PROGRESSIVE_SUBPATH="${MCP_PROGRESSIVE_SUBPATH:-}"
export GTS_CALLER="${GTS_CALLER:-mcp}"
export WORK_PATH="${WORK_PATH:-/opt/data}"
export MCP_LOG_DIR="${MCP_LOG_DIR:-${WORK_PATH}/logs}"
export PYTHONPATH="${GTS_MCP_ROOT}/src:${GTS_MCP_ROOT}/src/_generated:${PYTHONPATH:-}"

mkdir -p "${MCP_LOG_DIR}"

if [[ -z "${MCP_PATH// }" ]]; then
  export MCP_PATH=/
fi

_prepend_path() {
  local d="$1"
  if [[ -d "${d}" ]]; then
    case ":${PYTHONPATH:-}:" in
      *":${d}:"*) ;;
      *) export PYTHONPATH="${d}${PYTHONPATH:+:${PYTHONPATH}}" ;;
    esac
  fi
}

# 运行时以 /opt/mcp（pip --target）为准；勿把 /app/mcp 插到最前，否则热更新/挂载会失效
_prepend_path "${GTS_MCP_ROOT}/src/_generated"
_prepend_path "${GTS_MCP_ROOT}/src"

run_stdio() {
  if command -v gangtise-mcp >/dev/null 2>&1; then
    exec gangtise-mcp "$@"
  fi
  exec python -c "from stdio_server import main; import sys; main(sys.argv[1:])" "$@"
}

run_api() {
  if command -v gangtise-mcp-api >/dev/null 2>&1; then
    exec gangtise-mcp-api "$@"
  fi
  exec python -c "from http_server import main; import sys; main(sys.argv[1:])" "$@"
}

if [[ "${MCP_TRANSPORT}" == "stdio" ]]; then
  run_stdio "$@"
fi

EXTRA=(
  --transport "${MCP_TRANSPORT}"
  --layout unified
  --host "${MCP_HOST}"
  --port "${MCP_PORT}"
)
run_api "${EXTRA[@]}" "$@"
