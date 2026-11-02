# Unified Gangtise MCP image
#
# From repo root, after `python3 scripts/generate.py`:
#   docker build -t gangtise-mcp -f mcp/Dockerfile .
#
# Image contains only mcp/ (generated core+handlers live under mcp/src/_generated).

ARG BASE_IMAGE=python:3.11.9
FROM ${BASE_IMAGE}

WORKDIR /app

ARG OBS_ACCESS_KEY=
ARG OBS_SECRET_KEY=
ARG OBS_ENDPOINT=
ARG OBS_BUCKET=
ARG OBS_PATH=
ARG MCP_ATTACH_MAX_BYTES=33554432
ARG INSTALL_OBS=
ARG PIP_INDEX_URL=
ARG PIP_EXTRA_INDEX_URL=
ARG PIP_TRUSTED_HOST=

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_LAYOUT=unified \
    MCP_PATH=/ \
    SUBPATHS= \
    MCP_STATELESS=true \
    MCP_JSON_RESPONSE=true \
    MCP_REQUIRE_AUTH=true \
    MCP_TOOL_BLACKLIST= \
    GTS_SAVE_FILE=False \
    WORK_PATH=/opt/data \
    GTS_MCP_ROOT=/opt/mcp \
    TOOL_URL_DEPS_PATH=/opt/mcp/tool_url_deps.json \
    MCP_ATTACH_MAX_BYTES=${MCP_ATTACH_MAX_BYTES} \
    OBS_ACCESS_KEY=${OBS_ACCESS_KEY} \
    OBS_SECRET_KEY=${OBS_SECRET_KEY} \
    OBS_ENDPOINT=${OBS_ENDPOINT} \
    OBS_BUCKET=${OBS_BUCKET} \
    OBS_PATH=${OBS_PATH} \
    TZ=CST-8 \
    GTS_TOKEN_CACHE_PATH=/opt/data/auth_token_cache.json \
    PYTHONPATH=/opt/mcp/src:/opt/mcp/src/_generated

COPY mcp/entrypoint.sh /entrypoint.sh
COPY mcp /app/mcp

RUN set -eux; \
    PIP_OPTS=""; \
    if [ -n "${PIP_INDEX_URL}" ]; then PIP_OPTS="${PIP_OPTS} -i ${PIP_INDEX_URL}"; fi; \
    if [ -n "${PIP_EXTRA_INDEX_URL}" ]; then PIP_OPTS="${PIP_OPTS} --extra-index-url ${PIP_EXTRA_INDEX_URL}"; fi; \
    if [ -n "${PIP_TRUSTED_HOST}" ]; then PIP_OPTS="${PIP_OPTS} --trusted-host ${PIP_TRUSTED_HOST}"; fi; \
    chmod +x /entrypoint.sh; \
    mkdir -p /opt/data /opt/mcp; \
    test -d /app/mcp/src/_generated/gangtise_core; \
    pip install --upgrade pip ${PIP_OPTS}; \
    pip install ${PIP_OPTS} \
        "mcp>=1.0.0,<2" \
        "uvicorn>=0.30.0" \
        "httpx>=0.27.0" \
        "requests>=2.32.5" \
        "pandas>=2.2.3" \
        "pyyaml>=6.0" \
        "starlette>=0.37.0" \
        "PyJWT>=2.8.0" \
        "cryptography>=42.0.0"; \
    pip install --no-deps --target /opt/mcp/src ${PIP_OPTS} /app/mcp; \
    if [ -n "${INSTALL_OBS}" ] || { [ -n "${OBS_ACCESS_KEY}" ] && [ -n "${OBS_SECRET_KEY}" ] && [ -n "${OBS_ENDPOINT}" ] && [ -n "${OBS_BUCKET}" ]; }; then \
         pip install ${PIP_OPTS} "esdk-obs-python>=3.24.12"; \
       fi; \
    rm -rf /root/.cache/pip

RUN mkdir -p /opt/data
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
