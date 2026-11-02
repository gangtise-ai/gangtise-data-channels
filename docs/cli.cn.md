# CLI

**简体中文** | [English](cli.md)

命令行与 MCP 使用同一套工具。入口是 **`gangtise`**（仓库 [`cli/`](../cli/)）。

账号：[开放平台](https://open-platform.gangtise.com/) 的 Access Key / Secret Key。

中文示例使用 Gitee：[`https://gitee.com/gangtise/gangtise-data-channels`](https://gitee.com/gangtise/gangtise-data-channels)。英文示例见 [cli.md](cli.md)。

---

## 安装

需已安装 [uv](https://docs.astral.sh/uv/)。不必克隆仓库：

```bash
uvx --default-index https://pypi.tuna.tsinghua.edu.cn/simple \
  --from "git+https://gitee.com/gangtise/gangtise-data-channels#subdirectory=cli" \
  gangtise --help
```

之后：

```bash
uvx --default-index https://pypi.tuna.tsinghua.edu.cn/simple \
  --from "git+https://gitee.com/gangtise/gangtise-data-channels#subdirectory=cli" \
  gangtise list
```

---

## 凭证

```bash
uvx --default-index https://pypi.tuna.tsinghua.edu.cn/simple \
  --from "git+https://gitee.com/gangtise/gangtise-data-channels#subdirectory=cli" \
  gangtise configure --access-key <AK> --secret-key <SK>

# 环境变量优先于本地文件
export GTS_ACCESS_KEY=<AK>
export GTS_SECRET_KEY=<SK>
```

| 变量 | 说明 |
|------|------|
| `GTS_ACCESS_KEY` / `GTS_SECRET_KEY` | AK/SK |
| `GTS_AUTHORIZATION_PATH` | 凭证文件路径，默认 `~/.config/gangtise/authorization` |
| `GTS_AUTHORIZATION` | 直接使用的 Bearer |
| `GTS_SAVE_FILE` / `WORK_PATH` | 是否落盘 / 工作区 |

---

## 常用命令

| 命令 | 说明 |
|------|------|
| `gangtise configure` | 保存 AK/SK |
| `gangtise list` | 列出工具 |
| `gangtise <tool> --help` | 查看参数 |
| `gangtise <tool> ...` | 调用工具 |
| `gangtise uninstall` | 删除本地凭证文件 |

```bash
gangtise quote --securities 比亚迪
gangtise list
```

---

<details>
<summary><b>从源码运行</b></summary>

```bash
cd cli
uv sync --default-index https://pypi.tuna.tsinghua.edu.cn/simple
uv run gangtise list
```

</details>

---

[HTTP / SSE](http-sse.cn.md) · [Docker 部署](docker-deploy.cn.md) · [总览](../README.cn.md)
