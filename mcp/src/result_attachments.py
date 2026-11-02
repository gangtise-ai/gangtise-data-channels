"""从工具文本结果中提取本地路径，并以 MCP EmbeddedResource 附带返回。

- 单文件：原样传输（不压缩），按扩展名推断 mimeType
- 目录：打成 zip 后传输
- 文本中的 `` `/abs/path` `` 就地替换为 ``附件: `附件名` ``；
  准备失败则替换为失败说明；超过 ``_MAX_ATTACH_BYTES`` 时若配置了 OBS
  则上传并在正文给出下载链接，否则说明过大已跳过
- ``MCP_ATTACH_OBS_ALWAYS=true``（且已配 OBS）时：任意大小均上传 OBS，
  正文只返回链接（不嵌入 EmbeddedResource），便于 WorkBuddy 等不解析附件的客户端
- OBS 对象默认 1 天过期自动删除（``OBS_EXPIRE_DAYS``，见 ``obs_upload``）
- 嵌入附件、OBS 上传，或准备失败 / 过大跳过：默认清理 ``WORK_PATH`` 下对应本地文件并打日志
  （``MCP_CLEANUP_LOCAL_AFTER_ATTACH``，默认 true；未开附件时不会走此逻辑）
- ``with_path_attachments``（enabled）默认同步附着；仅下载类工具或检出重型
  文件（pdf/zip 等、目录、超阈值）时异步提交 job，返回 ``job_id``，由
  ``get_job_result`` 轮询。检索落盘的小结果（csv/md 列表）不走异步。
"""
from __future__ import annotations

import base64
import io
import logging
import mimetypes
import os
import re
import shutil
import zipfile
from typing import List, Optional, Tuple, Union
from urllib.parse import quote

from mcp.types import BlobResourceContents, EmbeddedResource, TextContent

from obs_upload import EXPIRE_DAYS as _OBS_EXPIRE_DAYS
from obs_upload import is_configured as obs_is_configured
from obs_upload import try_upload_bytes

ContentItem = Union[TextContent, EmbeddedResource]

logger = logging.getLogger("gangtise.result_attachments")

# 反引号包裹的 Unix 绝对路径：`/abs/path`（服务部署于 Linux / macOS）
_TICK_PATH_RE = re.compile(r"`(/[^`\n]+)`")
# 兼容尚未加反引号的 Unix 绝对路径
_BARE_ABS_RE = re.compile(r"(?<![`\w:])(/(?:[^\s`\"'<>|]+))")

# 默认最大嵌入附件体积；超出则改走 OBS（若已配置）
_MAX_ATTACH_BYTES = int(os.getenv("MCP_ATTACH_MAX_BYTES", str(32 * 1024 * 1024)))

# 显式下载 / 重处理工具：附着阶段可能超时，走异步 job
_ASYNC_ATTACH_TOOLS = frozenset(
    t.strip()
    for t in (os.getenv("MCP_ATTACH_ASYNC_TOOLS") or "get_file,pdf_parse").split(",")
    if t.strip()
)
# 非下载工具：单文件超过该字节才异步（默认 1MiB；检索 md/csv 通常远小于此）
_ASYNC_ATTACH_MIN_BYTES = int(os.getenv("MCP_ATTACH_ASYNC_MIN_BYTES", str(1024 * 1024)))
_HEAVY_ATTACH_SUFFIXES = (
    ".pdf",
    ".zip",
    ".docx",
    ".doc",
    ".pptx",
    ".ppt",
    ".xlsx",
    ".xls",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".mp3",
    ".mp4",
    ".wav",
)


def _env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


def cleanup_local_after_attach_enabled() -> bool:
    """附件/OBS 成功后是否删除本地源文件。"""
    return _env_flag("MCP_CLEANUP_LOCAL_AFTER_ATTACH", "true")


def attach_obs_always_enabled() -> bool:
    """是否强制所有附件走 OBS 链接（不嵌入 blob）。"""
    return _env_flag("MCP_ATTACH_OBS_ALWAYS", "false")


def _under_work_path(path: str) -> bool:
    """仅清理 WORK_PATH 下文件，避免误删正文里其它绝对路径。"""
    work = (os.getenv("WORK_PATH") or "").strip()
    if not work:
        return True
    try:
        norm = os.path.abspath(path)
        root = os.path.abspath(work)
        return norm == root or norm.startswith(root + os.sep)
    except Exception:
        return False


def _cleanup_local(path: str, *, reason: str = "") -> None:
    if not cleanup_local_after_attach_enabled():
        return
    if not path or not _under_work_path(path):
        return
    try:
        if os.path.isfile(path):
            os.remove(path)
            logger.info("cleaned local file path=%s reason=%s", path, reason or "ok")
        elif os.path.isdir(path):
            shutil.rmtree(path)
            logger.info("cleaned local dir path=%s reason=%s", path, reason or "ok")
    except OSError as e:
        logger.warning("cleanup failed path=%s reason=%s err=%s", path, reason or "ok", e)


def extract_local_paths(text: str) -> List[Tuple[str, str]]:
    """提取 (原文路径, 规范化绝对路径)，反引号优先，去重保序。"""
    if not text:
        return []
    found: List[Tuple[str, str]] = []
    seen: set[str] = set()

    def _add(raw: str) -> None:
        p = raw.strip().rstrip(".,;:)")
        # 仅处理服务端 Unix 路径；跳过客户端 Windows 路径（含 \），避免正则 \U 转义错误
        if not p.startswith("/") or p.startswith("//") or "\\" in p:
            return
        try:
            norm = os.path.abspath(p)
        except Exception:
            return
        if norm in seen:
            return
        seen.add(norm)
        found.append((p, norm))

    for m in _TICK_PATH_RE.finditer(text):
        _add(m.group(1))
    for m in _BARE_ABS_RE.finditer(text):
        _add(m.group(1))
    return found


# 常见扩展名补充（部分环境 mimetypes 未收录）
_EXTRA_MIME = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".html": "text/html",
    ".htm": "text/html",
}


def _guess_mime(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in _EXTRA_MIME:
        return _EXTRA_MIME[ext]
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def _unique_name(name: str, used: set[str]) -> str:
    if name not in used:
        used.add(name)
        return name
    stem, ext = os.path.splitext(name)
    i = 1
    while f"{stem}({i}){ext}" in used:
        i += 1
    out = f"{stem}({i}){ext}"
    used.add(out)
    return out


def _display_name(path: str, *, is_dir: bool = False) -> str:
    base = os.path.basename(path.rstrip("/")) or "attachment"
    if is_dir and not base.endswith(".zip"):
        return f"{base}.zip"
    return base


def _read_file_attachment(path: str) -> Tuple[str, str, bytes]:
    """单文件原样读取，返回 (文件名, mimeType, 字节)。"""
    name = os.path.basename(path) or "attachment.bin"
    with open(path, "rb") as f:
        data = f.read()
    return name, _guess_mime(name), data


def _zip_directory(path: str) -> Tuple[str, bytes]:
    """目录打 zip，返回 (zip 文件名, 字节)。"""
    base = os.path.basename(path.rstrip("/")) or "attachment"
    zip_name = f"{base}.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(path):
            for fn in files:
                full = os.path.join(root, fn)
                if not os.path.isfile(full):
                    continue
                arc = os.path.join(base, os.path.relpath(full, path))
                zf.write(full, arcname=arc.replace("\\", "/"))
    return zip_name, buf.getvalue()


def _label_ok(name: str) -> str:
    return f"附件: `{name}`"


def _label_fail(name: str, reason: str) -> str:
    return f"附件: `{name}` {reason}"


def _label_obs(name: str, url: str, *, oversized: bool = False) -> str:
    days = int(_OBS_EXPIRE_DAYS)
    ttl = f"{days}天有效，到期自动删除"
    tip = "可直接下载该文件查看完整数据。"
    if oversized:
        return f"附件: `{name}` 过大已上传 OBS（{ttl}）: {url}\n{tip}"
    return f"附件: `{name}` 下载链接（{ttl}）: {url}\n{tip}"


def _rewrite_paths(text: str, replacements: List[Tuple[str, str, str]]) -> str:
    """将文本中的绝对路径替换为标签。replacements: (原文路径, 规范化路径, 替换文本)。"""
    out = text
    # 先替换更长路径，避免前缀误伤
    ordered = sorted(replacements, key=lambda x: max(len(x[0]), len(x[1])), reverse=True)
    for raw, norm, label in ordered:
        for path in dict.fromkeys((raw, norm)):
            out = out.replace(f"`{path}`", label)
            # 裸路径仅做整段替换时风险较高，仅额外替换尚未被反引号包裹的完整路径 token
            out = re.sub(
                rf"(?<![`\w:]){re.escape(path)}(?![`\w])",
                label,
                out,
            )
    return out


def _try_obs_upload(
    data: bytes,
    name: str,
    mime: str,
    *,
    oversized: bool,
) -> Tuple[Optional[str], Optional[str]]:
    """返回 (url, error_message)。成功时 error 为 None。"""
    if not obs_is_configured():
        return None, "OBS 未配置"
    try:
        url = try_upload_bytes(data, name, content_type=mime)
        if url:
            return url, None
        return None, "OBS 上传返回空 URL"
    except Exception as e:
        logger.warning("obs upload failed name=%s size=%s err=%s", name, len(data), e)
        return None, str(e)


def build_path_attachments(
    text: str,
    *,
    enabled: bool = True,
    max_bytes: int = _MAX_ATTACH_BYTES,
) -> Tuple[str, List[EmbeddedResource]]:
    """
    扫描文本中的本地路径并附带返回：
    - 默认：小文件嵌入 EmbeddedResource；过大且已配 OBS → 正文下载链接
    - ``MCP_ATTACH_OBS_ALWAYS``：已配 OBS 时全部上传，正文只给链接（无 EmbeddedResource）
    - 准备失败 / 过大未配 OBS / OBS 失败：正文说明原因；默认仍清理本地
    返回 (改写后文本, 附件列表)
    """
    if not enabled:
        return text or "", []

    attachments: List[EmbeddedResource] = []
    replacements: List[Tuple[str, str, str]] = []
    used_names: set[str] = set()
    cleanup_paths: List[Tuple[str, str]] = []
    force_obs = attach_obs_always_enabled()

    for raw, norm in extract_local_paths(text):
        if not os.path.exists(norm):
            continue
        try:
            if os.path.isfile(norm):
                name, mime, data = _read_file_attachment(norm)
                name = _unique_name(name, used_names)
            elif os.path.isdir(norm):
                name, data = _zip_directory(norm)
                name = _unique_name(name, used_names)
                mime = "application/zip"
            else:
                continue
        except Exception as e:
            hint = _display_name(norm, is_dir=os.path.isdir(norm))
            logger.warning("attach prepare failed path=%s err=%s", norm, e)
            replacements.append((raw, norm, _label_fail(hint, f"准备失败：{e}")))
            cleanup_paths.append((norm, f"prepare_failed:{e}"))
            continue

        oversized = len(data) > max_bytes
        use_obs = force_obs or oversized

        if use_obs:
            url, err = _try_obs_upload(data, name, mime, oversized=oversized)
            if url:
                replacements.append(
                    (raw, norm, _label_obs(name, url, oversized=oversized and not force_obs))
                )
                cleanup_paths.append((norm, "obs_uploaded"))
                continue
            if force_obs:
                replacements.append(
                    (
                        raw,
                        norm,
                        _label_fail(
                            name,
                            f"OBS 上传失败（{len(data)} bytes）：{err or 'unknown'}",
                        ),
                    )
                )
                cleanup_paths.append((norm, f"obs_failed:{err}"))
                continue
            # oversized 且 OBS 失败/未配置
            if err and err != "OBS 未配置":
                replacements.append(
                    (
                        raw,
                        norm,
                        _label_fail(
                            name,
                            f"过大且 OBS 上传失败（{len(data)} bytes）：{err}",
                        ),
                    )
                )
                cleanup_paths.append((norm, f"obs_failed:{err}"))
                continue
            logger.warning(
                "attach skipped oversized path=%s size=%s limit=%s (OBS not configured)",
                norm,
                len(data),
                max_bytes,
            )
            replacements.append(
                (
                    raw,
                    norm,
                    _label_fail(
                        name, f"过大已跳过（{len(data)} bytes，上限 {max_bytes}）"
                    ),
                )
            )
            cleanup_paths.append((norm, f"oversized_no_obs:{len(data)}"))
            continue

        safe_name = quote(name, safe="._-")
        attachments.append(
            EmbeddedResource(
                type="resource",
                resource=BlobResourceContents(
                    uri=f"attachment://{safe_name}",
                    mimeType=mime,
                    blob=base64.b64encode(data).decode("ascii"),
                ),
            )
        )
        replacements.append((raw, norm, _label_ok(name)))
        cleanup_paths.append((norm, "embedded"))

    rewritten = _rewrite_paths(text or "", replacements)
    for path, reason in cleanup_paths:
        _cleanup_local(path, reason=reason)
    return rewritten, attachments


def _existing_attach_paths(text: str) -> List[Tuple[str, str]]:
    """正文中存在于磁盘的本地路径（文件或目录）。"""
    out: List[Tuple[str, str]] = []
    for raw, norm in extract_local_paths(text):
        try:
            if os.path.isfile(norm) or os.path.isdir(norm):
                out.append((raw, norm))
        except OSError:
            continue
    return out


def _needs_async_attach(
    text: str,
    *,
    source_tool: Optional[str] = None,
) -> bool:
    """仅下载类 / 重型附件走异步；检索落盘的小 md/csv 同步返回。"""
    paths = _existing_attach_paths(text)
    if not paths:
        return False
    tool = (source_tool or "").strip()
    if tool in _ASYNC_ATTACH_TOOLS:
        return True
    for _, norm in paths:
        try:
            if os.path.isdir(norm):
                return True
            if not os.path.isfile(norm):
                continue
            lower = norm.lower()
            if any(lower.endswith(suf) for suf in _HEAVY_ATTACH_SUFFIXES):
                return True
            if os.path.getsize(norm) >= _ASYNC_ATTACH_MIN_BYTES:
                return True
        except OSError:
            continue
    return False


def with_path_attachments(
    text: str,
    *,
    enabled: bool = True,
    source_tool: Optional[str] = None,
    sync: bool = False,
) -> List[ContentItem]:
    """文本结果 + 可选路径附件。

    enabled 时默认同步附着。仅 ``get_file`` / ``pdf_parse`` 等下载类工具，
    或正文含重型文件（pdf/zip/目录/超 ``MCP_ATTACH_ASYNC_MIN_BYTES``）时异步
    提交 job（返回 pending + job_id）。``sync=True`` 强制同步。
    """
    if not enabled:
        return [TextContent(type="text", text=text or "")]

    if not sync and _needs_async_attach(text, source_tool=source_tool):
        from attach_jobs import pending_message, submit_attach_job

        job_id = submit_attach_job(text or "", source_tool=source_tool)
        return [TextContent(type="text", text=pending_message(job_id, source_tool=source_tool))]

    body, attachments = build_path_attachments(text, enabled=True)
    items: List[ContentItem] = [TextContent(type="text", text=body)]
    items.extend(attachments)
    return items
