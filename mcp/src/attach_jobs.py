"""异步附件 job：磁盘状态 + 线程池执行 build_path_attachments。

目录：{WORK_PATH}/attach_jobs/{job_id}/
  meta.json / input.txt / result.json / blobs/*
"""
from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, unquote

from mcp.types import BlobResourceContents, EmbeddedResource, TextContent

logger = logging.getLogger("gangtise.attach_jobs")

_POLL_HINT_SEC = 3
_DEFAULT_TTL_HOURS = 24
_DEFAULT_WORKERS = 4

_lock = threading.Lock()
_executor: Optional[ThreadPoolExecutor] = None


def _ttl_seconds() -> float:
    raw = (os.getenv("MCP_ATTACH_JOB_TTL_HOURS") or str(_DEFAULT_TTL_HOURS)).strip()
    try:
        hours = float(raw)
    except ValueError:
        hours = float(_DEFAULT_TTL_HOURS)
    return max(1.0, hours) * 3600.0


def _worker_count() -> int:
    raw = (os.getenv("MCP_ATTACH_JOB_WORKERS") or str(_DEFAULT_WORKERS)).strip()
    try:
        n = int(raw)
    except ValueError:
        n = _DEFAULT_WORKERS
    return max(1, min(32, n))


def _work_root() -> Path:
    work = (os.getenv("WORK_PATH") or os.getenv("GTS_WORK_PATH") or "").strip()
    if not work:
        work = os.path.join(os.path.expanduser("~"), "gangtise")
    return Path(work)


def jobs_root() -> Path:
    root = _work_root() / "attach_jobs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _job_dir(job_id: str) -> Path:
    return jobs_root() / job_id


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    with _lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=_worker_count(),
                thread_name_prefix="attach-job",
            )
        return _executor


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _cleanup_expired() -> None:
    root = jobs_root()
    ttl = _ttl_seconds()
    now = time.time()
    try:
        entries = list(root.iterdir())
    except OSError:
        return
    for entry in entries:
        if not entry.is_dir():
            continue
        meta = _read_json(entry / "meta.json")
        created = None
        if meta is not None:
            try:
                created = float(meta.get("created_at") or 0)
            except (TypeError, ValueError):
                created = 0.0
        if created is None or created <= 0:
            try:
                created = entry.stat().st_mtime
            except OSError:
                continue
        if now - created > ttl:
            try:
                shutil.rmtree(entry)
                logger.info("attach job expired removed job_id=%s", entry.name)
            except OSError as e:
                logger.warning("attach job cleanup failed job_id=%s err=%s", entry.name, e)


def pending_message(job_id: str, *, source_tool: Optional[str] = None) -> str:
    lines = [
        "附件处理已提交为异步任务。",
        f"job_id: `{job_id}`",
        "status: pending",
    ]
    if source_tool:
        lines.append(f"source_tool: `{source_tool}`")
    lines.append(
        f"请调用工具 `get_job_result`，传入上述 job_id 轮询结果"
        f"（建议间隔 {_POLL_HINT_SEC} 秒，直至 status 为 success 或 failed）。"
    )
    return "\n".join(lines)


def _serialize_result(
    job_dir: Path,
    text: str,
    attachments: List[EmbeddedResource],
) -> Dict[str, Any]:
    blobs_dir = job_dir / "blobs"
    items: List[Dict[str, Any]] = []
    for att in attachments:
        res = att.resource
        uri = str(getattr(res, "uri", "") or "")
        mime = str(getattr(res, "mimeType", "") or "application/octet-stream")
        blob_b64 = str(getattr(res, "blob", "") or "")
        name = unquote(uri.split("://", 1)[-1]) if "://" in uri else (uri or "attachment.bin")
        safe = quote(name, safe="._-")
        entry: Dict[str, Any] = {"uri": uri or f"attachment://{safe}", "mimeType": mime, "name": name}
        if blob_b64:
            blobs_dir.mkdir(parents=True, exist_ok=True)
            blob_path = blobs_dir / safe
            try:
                blob_path.write_bytes(base64.b64decode(blob_b64))
                entry["blob_file"] = f"blobs/{safe}"
            except Exception:
                entry["blob_b64"] = blob_b64
        items.append(entry)
    return {"text": text or "", "attachments": items}


def _deserialize_result(job_dir: Path, data: Dict[str, Any]) -> List[Any]:
    text = str(data.get("text") or "")
    items: List[Any] = [TextContent(type="text", text=text)]
    for att in data.get("attachments") or []:
        if not isinstance(att, dict):
            continue
        uri = str(att.get("uri") or "")
        mime = str(att.get("mimeType") or "application/octet-stream")
        blob_b64 = ""
        blob_file = att.get("blob_file")
        if blob_file:
            path = job_dir / str(blob_file)
            if path.is_file():
                blob_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        if not blob_b64:
            blob_b64 = str(att.get("blob_b64") or "")
        if not uri or not blob_b64:
            continue
        items.append(
            EmbeddedResource(
                type="resource",
                resource=BlobResourceContents(
                    uri=uri,
                    mimeType=mime,
                    blob=blob_b64,
                ),
            )
        )
    return items


def _run_job(job_id: str) -> None:
    # 延迟导入，避免与 result_attachments 循环依赖
    from result_attachments import build_path_attachments

    job_dir = _job_dir(job_id)
    meta_path = job_dir / "meta.json"
    input_path = job_dir / "input.txt"
    try:
        text = input_path.read_text(encoding="utf-8") if input_path.is_file() else ""
        body, attachments = build_path_attachments(text, enabled=True)
        result = _serialize_result(job_dir, body, attachments)
        _write_json(job_dir / "result.json", result)
        meta = _read_json(meta_path) or {}
        meta["status"] = "success"
        meta["finished_at"] = time.time()
        meta.pop("error", None)
        _write_json(meta_path, meta)
        logger.info("attach job success job_id=%s attachments=%s", job_id, len(attachments))
    except Exception as e:
        logger.exception("attach job failed job_id=%s", job_id)
        meta = _read_json(meta_path) or {"job_id": job_id, "created_at": time.time()}
        meta["status"] = "failed"
        meta["finished_at"] = time.time()
        meta["error"] = str(e)
        _write_json(meta_path, meta)


def submit_attach_job(text: str, *, source_tool: Optional[str] = None) -> str:
    """创建 pending job 并提交后台处理，立即返回 job_id。"""
    _cleanup_expired()
    job_id = uuid.uuid4().hex
    job_dir = _job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "input.txt").write_text(text or "", encoding="utf-8")
    meta = {
        "job_id": job_id,
        "status": "pending",
        "created_at": time.time(),
        "source_tool": source_tool,
    }
    _write_json(job_dir / "meta.json", meta)
    _get_executor().submit(_run_job, job_id)
    return job_id


def read_job(job_id: str) -> Tuple[str, Optional[str], Optional[List[Any]]]:
    """返回 (status, error_or_none, content_items_or_none)。

    status: pending | success | failed | not_found
    """
    _cleanup_expired()
    jid = (job_id or "").strip()
    if not jid or "/" in jid or "\\" in jid or jid in (".", ".."):
        return "not_found", "无效的 job_id", None
    job_dir = _job_dir(jid)
    meta = _read_json(job_dir / "meta.json")
    if meta is None:
        return "not_found", f"未找到 job_id: {jid}", None
    status = str(meta.get("status") or "pending").lower()
    if status == "pending":
        return "pending", None, None
    if status == "failed":
        return "failed", str(meta.get("error") or "附件处理失败"), None
    if status == "success":
        result = _read_json(job_dir / "result.json")
        if result is None:
            return "failed", "job 结果文件缺失", None
        return "success", None, _deserialize_result(job_dir, result)
    return "failed", f"未知 status: {status}", None
