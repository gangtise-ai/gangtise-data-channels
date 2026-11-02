# CLI

[简体中文](cli.cn.md) | **English**

The CLI calls the same tools as MCP. The entry command is **`gangtise`** ([`cli/`](../cli/)).

Credentials: Access Key / Secret Key from the [open platform](https://open-platform.gangtise.com/).

Examples use GitHub: [`https://github.com/gangtise-ai/gangtise-data-channels`](https://github.com/gangtise-ai/gangtise-data-channels). Chinese examples use Gitee: [cli.cn.md](cli.cn.md).

---

## Install

Requires [uv](https://docs.astral.sh/uv/). No clone needed:

```bash
uvx --from "git+https://github.com/gangtise-ai/gangtise-data-channels#subdirectory=cli" \
  gangtise --help
```

Then:

```bash
uvx --from "git+https://github.com/gangtise-ai/gangtise-data-channels#subdirectory=cli" \
  gangtise list
```

---

## Credentials

```bash
uvx --from "git+https://github.com/gangtise-ai/gangtise-data-channels#subdirectory=cli" \
  gangtise configure --access-key <AK> --secret-key <SK>

# env overrides the local file
export GTS_ACCESS_KEY=<AK>
export GTS_SECRET_KEY=<SK>
```

| Variable | Notes |
|----------|--------|
| `GTS_ACCESS_KEY` / `GTS_SECRET_KEY` | AK/SK |
| `GTS_AUTHORIZATION_PATH` | Credentials file; default `~/.config/gangtise/authorization` |
| `GTS_AUTHORIZATION` | Bearer to use directly |
| `GTS_SAVE_FILE` / `WORK_PATH` | Persist outputs / workspace |

---

## Common commands

| Command | Notes |
|---------|--------|
| `gangtise configure` | Save AK/SK |
| `gangtise list` | List tools |
| `gangtise <tool> --help` | Tool help |
| `gangtise <tool> ...` | Invoke a tool |
| `gangtise uninstall` | Remove the local credentials file |

```bash
gangtise quote --securities 比亚迪
gangtise list
```

---

<details>
<summary><b>Run from source</b></summary>

```bash
cd cli
uv sync
uv run gangtise list
```

</details>

---

[HTTP / SSE](http-sse.md) · [Docker](docker-deploy.md) · [Overview](../README.md)
