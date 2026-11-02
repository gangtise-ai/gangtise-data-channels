#!/usr/bin/env bash
# Build the test image, start it locally, and smoke-test MCP + CLI.
#
#   scripts/docker_test.sh            # build + run + smoke
#   scripts/docker_test.sh --no-build # reuse the existing image
#   scripts/docker_test.sh --stop     # remove the container
#
# Env: IMAGE (gangtise-data-channels:test), NAME (gangtise-test), PORT (8000),
#      GTS_ACCESS_KEY / GTS_SECRET_KEY (optional; enables a live CLI call),
#      PIP_INDEX_URL (optional mirror for the build),
#      BASE_IMAGE (optional local base when Docker Hub is unreachable,
#      e.g. BASE_IMAGE=gangtise-mcp:latest).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${IMAGE:-gangtise-data-channels:test}"
NAME="${NAME:-gangtise-test}"
PORT="${PORT:-8000}"
BUILD=1

for arg in "$@"; do
  case "$arg" in
    --no-build) BUILD=0 ;;
    --stop) docker rm -f "$NAME" >/dev/null 2>&1 || true; echo "removed $NAME"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

cd "$ROOT"
fail() { echo "FAIL: $*" >&2; docker logs --tail 50 "$NAME" >&2 || true; exit 1; }
pass() { echo "ok   $*"; }

if [[ "$BUILD" == 1 ]]; then
  python3 scripts/generate.py
  docker build -t "$IMAGE" -f Dockerfile.test \
    ${BASE_IMAGE:+--build-arg BASE_IMAGE="$BASE_IMAGE"} \
    ${PIP_INDEX_URL:+--build-arg PIP_INDEX_URL="$PIP_INDEX_URL"} .
fi

docker rm -f "$NAME" >/dev/null 2>&1 || true
RUN_ENV=()
[[ -n "${GTS_ACCESS_KEY:-}" ]] && RUN_ENV+=(-e "GTS_ACCESS_KEY=$GTS_ACCESS_KEY")
[[ -n "${GTS_SECRET_KEY:-}" ]] && RUN_ENV+=(-e "GTS_SECRET_KEY=$GTS_SECRET_KEY")
docker run -d --name "$NAME" -p "${PORT}:8000" ${RUN_ENV[@]+"${RUN_ENV[@]}"} "$IMAGE" >/dev/null

for _ in $(seq 1 40); do
  curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1 && break
  sleep 0.5
done
curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null || fail "/health not reachable"
pass "GET /health"

MCP_HEADERS=(-H "Content-Type: application/json" -H "Accept: application/json, text/event-stream")
init=$(curl -fsS "${MCP_HEADERS[@]}" "http://127.0.0.1:${PORT}/" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"docker-test","version":"0"}}}') \
  || fail "MCP initialize"
grep -q '"serverInfo"' <<<"$init" || fail "MCP initialize: $init"
pass "MCP initialize"

tools=$(curl -fsS "${MCP_HEADERS[@]}" "http://127.0.0.1:${PORT}/" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}') || fail "MCP tools/list"
count=$(python3 -c 'import json,sys; print(len(json.loads(sys.stdin.read().split("data:",1)[-1])["result"]["tools"]))' <<<"$tools") \
  || fail "MCP tools/list: ${tools:0:300}"
[[ "$count" -gt 0 ]] || fail "MCP tools/list returned no tools"
pass "MCP tools/list ($count tools)"

docker exec "$NAME" gangtise --version || fail "gangtise --version"
docker exec "$NAME" gangtise list >/dev/null || fail "gangtise list"
pass "gangtise --version / list"

set +e
docker exec -e GTS_ACCESS_KEY=x -e GTS_SECRET_KEY=y "$NAME" \
  gangtise quote --securities 600519.SH --start-date 07/01/2026 >/dev/null 2>&1
rc=$?
set -e
[[ "$rc" == 2 ]] || fail "year-last date should exit 2, got $rc"
pass "CLI rejects year-last date with exit 2"

if [[ -n "${GTS_ACCESS_KEY:-}" && -n "${GTS_SECRET_KEY:-}" ]]; then
  docker exec "$NAME" gangtise security -k 贵州茅台 || fail "live CLI call"
  pass "live CLI call (security -k 贵州茅台)"
else
  echo "skip live CLI call (set GTS_ACCESS_KEY / GTS_SECRET_KEY to enable)"
fi

echo
echo "container $NAME is running on http://127.0.0.1:${PORT}/"
echo "  docker exec -it $NAME gangtise --help"
echo "  scripts/docker_test.sh --stop"
