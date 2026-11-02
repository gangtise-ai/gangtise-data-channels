# Gangtise Data Channels

skill 自包含、可独立运行；`core/` 是 MCP / CLI 的运行时真源，`mcp`、`cli` 里的 `_generated` 一律生成，禁止手改。

```
core/src/gangtise_core/          手改：信封、鉴权、Result、catalog（MCP / CLI 用）
skills/openapi/*/scripts/        手改：任务级 handlers，不依赖 gangtise_core
skills/openapi/*/references/     手改：工具 YAML
mcp/src/                         手改：stdio / HTTP 适配器（不含 _generated）
cli/src/gangtise_cli/            手改：CLI 适配器（不含 _generated）
scripts/generate.py              生成器：core + handlers → mcp/cli 的 _generated
scripts/check_skills.py          skill 一致性校验
```

每个 skill 的 `scripts/` 自带三份共享文件，**各 skill 间必须逐字节相同**：

- `gts_auth.py`：鉴权（AK/SK loginV2、token 缓存、失效重登）
- `gts_runtime.py`：错误类型、信封解析、按端点策略重试、fieldList 展开、时间换算、Result
- `_launch.py`：让 `python3 scripts/quote.py` 以包内模块运行（仅标准库）

改其中任何一份，要同步改到全部 skill；`check_skills.py` 会逐项校验：共享文件一致、skill 不导入 `gangtise_core`、共享文件导出的名字在 core 有同名实现、`ERROR_HINTS` / `PARAM_CODES` / 端点重试策略与 core 一致、脚本里没有未导入就使用的名字。

生成到 MCP / CLI 时不复制这三份文件，改写导入以共用 core 的请求级鉴权与错误类型：

```
from .gts_auth import     → from gangtise_core.auth import
from .gts_runtime import  → from gangtise_core.skill_runtime import
```

生成布局（mcp、cli 相同）：

```
<host>/_generated/gangtise_core/
<host>/_generated/handlers/<pkg>/
<host>/_generated/DO_NOT_EDIT
```

- skill：直接 `python3 skills/openapi/<skill>/scripts/quote.py`，无需生成步骤
- MCP：只读 `mcp/`（含已生成 `_generated`），不 PYTHONPATH 仓库 `core/` 或 `skills/`
- CLI：只读 `cli/`

改 core 或 skill 脚本后必须（generate 会先跑 skill 校验，不通过则不写）：

```bash
python3 scripts/generate.py
python3 scripts/generate.py --check
```

## 运行

```bash
python3 scripts/generate.py

# Skill（独立运行，只依赖本 skill 的 scripts/）
python3 skills/openapi/gangtise-data/scripts/quote.py --securities 茅台

# CLI
cd cli && uv sync
uv run gangtise list
uv run gangtise quote --securities 贵州茅台

# MCP stdio / HTTP
cd mcp && uv sync
uv run gangtise-mcp
uv run gangtise-mcp-api --host 0.0.0.0 --port 8000
```

打包 zip 会先跑 generate（skill 校验不通过则中止）；skill zip 只含该 skill 自己的文件，解压即可运行。

## 本地容器测试

`Dockerfile.test` 把 MCP HTTP 服务和 `gangtise` CLI 装进同一个镜像（仅供测试，默认 `MCP_REQUIRE_AUTH=false`）：

```bash
scripts/docker_test.sh                     # generate → build → run → 冒烟（/health、MCP initialize/tools/list、CLI）
PORT=18000 scripts/docker_test.sh          # 8000 被占用时换端口
GTS_ACCESS_KEY=… GTS_SECRET_KEY=… scripts/docker_test.sh   # 追加一次真实 CLI 调用
docker exec -it gangtise-test gangtise --help
scripts/docker_test.sh --stop
```

拉不到 Docker Hub 时用本地已有的 Python 3.10+ 镜像作底：
`DOCKER_BUILDKIT=0 BASE_IMAGE=gangtise-mcp:latest scripts/docker_test.sh`。

## 错误处理

与 [gangtise-openapi-cli](https://github.com/gangtiser/gangtise-openapi-cli) 对齐：

- 报错行：`API error (<code>) [trace <id>]: <msg> <hint>`；hint 来自 `core/src/gangtise_core/hints.py`（按码 + EDE 报错文本），MCP 返回 JSON 带 `hint` / `traceId`。
- 退出码：0 成功（含空结果）、1 失败、2 参数错误（本地校验或服务端参数类错误码）、3 部分成功；Ctrl-C 130、SIGTERM 143、SIGHUP 129；管道被关闭时保留已判定的退出码。
- 重试：`endpoints.yaml` 的 `retry` 取 `retry`（默认）/ `no-replay` / `no-999999`；999011、140002 永不重试；429 总是重试并遵守 Retry-After（上限 60s）；最多重试 2 次，400ms 起指数退避、上限 4s。
- 积分防护：按条计费的列表与观点正文下载，预计积分消耗较大时先拒绝，须 `--yes`（MCP 传 `confirm=true`）确认；默认开启，环境变量 `GANGTISE_CREDIT_GUARD=0`（或 `false` / `no` / `off`）关闭。
- 参数：日期接受 `YYYY-MM-DD` / `YYYY/MM/DD` / `YYYYMMDD` 并统一成 `YYYY-MM-DD`，拒绝年在后的写法；时间戳换算按北京时间；数值只收普通十进制（拒绝 `0x10`、`1e3`、`5.0`）。

## 鉴权

`gangtise configure --access-key … --secret-key …` 或环境变量 `GTS_ACCESS_KEY` / `GTS_SECRET_KEY`。
Token 按账号指纹落盘（`~/.cache/gangtise/token.json` 或 `GTS_TOKEN_CACHE_PATH`）。

## 开源边界

公开仓含 `core/`、`skills/openapi/`（含生成树）、`mcp/`（不含自有 yaml/启动脚本）、`cli/`、`scripts/`。
`skills/research`、`others`、`tools`、`system` 以及 `mcp/local_start.sh` 等见根目录 `.gitignore`。
