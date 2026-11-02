if __name__ == "__main__" and not __package__:
    import importlib.util
    from pathlib import Path as _P
    _launch = _P(__file__).resolve().parent / "_launch.py"
    _spec = importlib.util.spec_from_file_location("_gts_skill_launch", _launch)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(_mod)
    raise SystemExit(_mod.relaunch(__file__))

import os
import re
import sys
from datetime import datetime
from io import TextIOWrapper
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote
import pandas as pd

from .gts_runtime import unwrap
from .gts_runtime import ApiError, GangtiseError, PartialResultError, ValidationError
from .gts_runtime import request_json

from .utils import (
    DRIVE_COPY_URL,
    DRIVE_CREATE_FOLDER_URL,
    DRIVE_DELETE_FILE_URL,
    DRIVE_DELETE_FOLDER_URL,
    DRIVE_DOWNLOAD_URL,
    DRIVE_FOLDER_LIST_URL,
    DRIVE_LIST_URL,
    DRIVE_MOVE_FILE_URL,
    DRIVE_MOVE_FOLDER_URL,
    DRIVE_RENAME_URL,
    DRIVE_UPLOAD_URL,
    FILE_DEFAULT_LIMIT,
    authorized_request,
    format_response,
    check_version,
    get_authorization_token,
    is_code_arg,
)

DEFAULT_LIST_LIMIT = FILE_DEFAULT_LIMIT.get("private_cloud", 100)
IDS_FILE_HINT = "可以删除行或保留需要的文件，再通过 --files-file 参数下载"
METHOD = "private_cloud"

MODES = [
    "search",
    "get",
    "folder_list",
    "upload",
    "create_folder",
    "rename",
    "move_file",
    "move_folder",
    "copy",
    "delete_file",
    "delete_folder",
]

# 删除不可恢复：所有入口（脚本、CLI、MCP）都须显式确认，被拒后不要未经用户同意自行补确认重试。
_CONFIRM_HINT = "取得用户明确同意后再加 --yes（MCP 传 confirm=true）重试。"
DELETE_WARNINGS = {
    "delete_file": "已拒绝：删除的云盘文件无法恢复。先用 search 模式核对文件 ID 对应的文件名，" + _CONFIRM_HINT,
    "delete_folder": "已拒绝：删除文件夹会连同其中全部子文件夹与文件一起删除，且无法恢复。"
    "先用 folder_list 模式（--parent-id <id>）看清里面有什么，" + _CONFIRM_HINT,
}

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_NAME_LEN = 200
META_LOOKUP_MAX_SCAN = 2000

FILE_TYPE_MAP = {
    "文档": "document",
    "图片": "image",
    "音视频": "media",
    "视频": "media",
    "音频": "media",
    "公众号文章": "article",
    "文章": "article",
    "其他": "other",
}

FILE_TYPE_VALID = {"document", "image", "media", "article", "other"}

SPACE_TYPE_MAP = {
    "我的云盘": 1,
    "个人云盘": 1,
    "租户云盘": 2,
    "1": 1,
    "2": 2,
}


def _parse_str_list(raw: Any) -> Optional[List[str]]:
    if not raw:
        return None
    if isinstance(raw, (list, tuple, set)):
        raw = ",".join(str(x) for x in raw)
    items = [x.strip() for x in str(raw).replace("，", ",").split(",") if x.strip()]
    return items or None


def _normalize_datetime_field(raw: Optional[str], *, end_of_day: bool) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            return s
        return s + (" 23:59:59" if end_of_day else " 00:00:00")
    return s


def _normalize_file_type_list(items: Optional[List[str]]) -> Optional[List[str]]:
    if not items:
        return None
    out: List[str] = []
    for x in items:
        s = str(x).strip()
        if not s:
            continue
        key = s.lower()
        if s in FILE_TYPE_MAP:
            v = FILE_TYPE_MAP[s]
        elif key in FILE_TYPE_VALID:
            v = key
        else:
            v = FILE_TYPE_MAP.get(s, s)
        if v in FILE_TYPE_VALID and v not in out:
            out.append(v)
    return out or None


def _normalize_space_type(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s in SPACE_TYPE_MAP:
        return SPACE_TYPE_MAP[s]
    try:
        v = int(s)
    except ValueError:
        return None
    return v if v in (1, 2) else None


def _normalize_space_type_list(items: Optional[List[Any]]) -> Optional[List[int]]:
    if not items:
        return None
    out: List[int] = []
    for x in items:
        v = _normalize_space_type(x)
        if v is not None and v not in out:
            out.append(v)
    return out or None


def _name_length(name: str) -> int:
    return len(name.encode("utf-16-le")) // 2


def _check_api_ok(body: Dict[str, Any]) -> bool:
    code = body.get("code", "000000")
    return (code in (200, "000000") or code == "0") and body.get("status", True) is True


def _api_error_message(body: dict, fallback: str = "") -> str:
    if isinstance(body, dict):
        return str(body.get("msg") or body.get("message") or fallback)
    return fallback


def _require_auth() -> None:
    if not get_authorization_token():
        raise ApiError("未配置 gangtise 授权，无法调用 open 接口", code="999011")


def _success_message(message: str, output_dir: Optional[str] = None):
    return format_response({"state": "success", "message": message, "data": [], "usage": {}}, METHOD, output_dir=output_dir)


def _post(url: str, payload: dict, timeout: int = 120) -> Any:
    return request_json("POST", url, json=payload, timeout=timeout)


def _success_lines(action: str, data: Any) -> str:
    data = data if isinstance(data, dict) else {}
    success_list = data.get("successList") or []
    shown = []
    for x in success_list:
        if isinstance(x, dict):
            shown.append(f"{x.get('fileId')} → {x.get('newFileId')}")
        else:
            shown.append(str(x))
    msg = f"{action}完成：成功 {len(success_list)} 个"
    if shown:
        msg += "\n成功：" + "，".join(shown)
    return msg


def _flatten_drive_file(row: dict) -> dict:
    return {
        "file_id": row.get("fileId"),
        "title": row.get("title"),
        "create_time": row.get("createTime"),
        "space_type": row.get("spaceType"),
        "file_size": row.get("fileSize"),
        "url": row.get("url"),
        "uploader": row.get("uploader"),
    }


def _fetch_drive_list(
    *,
    page_from: int = 0,
    page_size: int = 20,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    keyword: Optional[str] = None,
    file_type_list: Optional[List[str]] = None,
    space_type_list: Optional[List[int]] = None,
    max_total: int = DEFAULT_LIST_LIMIT,
) -> Tuple[List[dict], int, Optional[str]]:
    cap = max(1, int(max_total))
    sz = min(50, max(1, int(page_size)))
    offset = max(0, int(page_from))
    aggregated: List[dict] = []
    total = 0
    part_err: Optional[str] = None

    st = _normalize_datetime_field(start_time, end_of_day=False)
    et = _normalize_datetime_field(end_time, end_of_day=True)

    while len(aggregated) < cap:
        chunk = min(sz, cap - len(aggregated))
        payload: Dict[str, Any] = {"from": offset, "size": chunk}
        if st:
            payload["startTime"] = st
        if et:
            payload["endTime"] = et
        if keyword:
            payload["keyword"] = str(keyword).strip()
        if file_type_list:
            payload["fileTypeList"] = file_type_list
        if space_type_list:
            payload["spaceTypeList"] = space_type_list

        try:
            data_block = _post(DRIVE_LIST_URL, payload, timeout=300)
        except GangtiseError as e:
            if not aggregated:
                raise
            part_err = str(e)
            break

        if isinstance(data_block, dict):
            total = int(data_block.get("total") or 0)
            raw_list = data_block.get("list") or []
        else:
            raw_list = []
        if not isinstance(raw_list, list):
            raw_list = []

        for row in raw_list:
            if isinstance(row, dict):
                aggregated.append(_flatten_drive_file(row))
        if len(raw_list) < chunk:
            break
        offset += len(raw_list)

    return aggregated, total, part_err


def _lookup_file_meta(file_ids: List[str], max_scan: int = META_LOOKUP_MAX_SCAN) -> Dict[str, dict]:
    """getList 不支持按 fileId 过滤，只能翻页扫描；对话/速记/翻译目录下的文件不会出现在列表中。"""
    pending = {str(x).strip() for x in file_ids if str(x).strip()}
    found: Dict[str, dict] = {}
    offset = 0
    while pending and offset < max_scan:
        try:
            data_block = _post(DRIVE_LIST_URL, {"from": offset, "size": 50}, timeout=300)
        except GangtiseError:
            break
        if not isinstance(data_block, dict):
            break
        raw_list = data_block.get("list") or []
        for row in raw_list:
            if not isinstance(row, dict):
                continue
            fid = str(row.get("fileId") or "").strip()
            if fid in pending:
                found[fid] = _flatten_drive_file(row)
                pending.discard(fid)
        if len(raw_list) < 50:
            break
        offset += len(raw_list)
    return found


def _parse_disposition_filename(disposition: Optional[str]) -> Optional[str]:
    if not disposition:
        return None
    m = re.search(r"filename\*\s*=\s*(?:utf-8|UTF-8)''([^;]+)", disposition)
    if not m:
        m = re.search(r'filename\s*=\s*"?([^";]+)"?', disposition, flags=re.IGNORECASE)
    return unquote(m.group(1).strip()) if m else None


def _build_local_filename(title: str, server_filename: Optional[str]) -> Optional[str]:
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", (title or "").strip()).strip(" .")
    if not name:
        return server_filename
    server_ext = os.path.splitext(server_filename or "")[1]
    if server_ext and not os.path.splitext(name)[1]:
        name += server_ext
    return name


def _download_drive_file(
    file_id: str,
    title: str = "",
    create_time: str = "",
    url: str = "",
) -> Tuple[Optional[dict], Optional[str]]:
    fid = str(file_id).strip()
    if not fid:
        return None, "fileId 为空"

    params = {"fileId": fid}
    try:
        r = authorized_request("GET", DRIVE_DOWNLOAD_URL, params=params, timeout=300)
    except Exception as e:
        return None, str(e)

    if r.status_code != 200:
        return None, f"下载 HTTP {r.status_code}: {r.text[:300]}"

    ctype_hdr = (r.headers.get("Content-Type") or "").lower()
    if "json" in ctype_hdr:
        try:
            body = r.json()
            if isinstance(body, dict) and ("code" in body or "status" in body) and not _check_api_ok(body):
                return None, _api_error_message(body, "下载失败")
        except Exception:
            pass

    if not r.content:
        return None, "下载内容为空"
    filename = _build_local_filename(title, _parse_disposition_filename(r.headers.get("Content-Disposition")))
    if filename:
        body_text = {"status": "success", "file_bytes": r.content, "filename": filename}
    else:
        body_text = {"status": "failed", "message": "文件名无法获取"}

    item = {
        "标题": title or fid,
        "文件时间": create_time or "",
        "文件内容": body_text,
        "链接": url or "",
        "文件ID": fid,
        "类型": "AI云盘",
        "类型ID": fid,
    }
    return item, None


def _load_file_ids_from_file(path: str) -> List[str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"云盘文件列表不存在: {path}")
    df = pd.read_csv(path)
    for col in ("file_id", "fileId", "类型ID"):
        if col in df.columns:
            return [str(x).strip() for x in df[col].dropna().tolist() if str(x).strip()]
    raise ValueError("文件须包含 file_id 或 fileId 列")


def _format_file_list(
    records: List[dict],
    total: int,
    part_err: Optional[str],
    append_file_hint: bool,
    output_dir: Optional[str],
    prefix: str = "",
):
    msg = prefix + f"已找到 {len(records)} 个云盘文件"
    if total:
        msg += f"（total={total}）"
    if append_file_hint:
        msg += f"；{IDS_FILE_HINT}"
    extra = f"\n未完整拉取：{part_err}" if part_err else ""
    return format_response(
        {
            "state": "success",
            "message": msg,
            "data": [{"data": records, "module": "private_cloud_list", "type": "data"}],
            "usage": {},
        },
        METHOD,
        output_dir=output_dir,
        additional_message=extra.strip(),
    )


def _exact_match_files(keyword: str, records: List[dict]) -> List[dict]:
    kw = keyword.strip()
    return [
        r
        for r in records
        if str(r.get("title") or "").strip() == kw
        or str(r.get("file_id") or "").strip() == kw
    ]


def _resolve_files_from_arg(
    raw: str,
    limit: int = DEFAULT_LIST_LIMIT,
    output_dir: Optional[str] = None,
    meta_out: Optional[Dict[str, dict]] = None,
    **search_kwargs,
) -> Tuple[Optional[List[str]], Optional[Any]]:
    """文件 ID 原样返回；标题经 search 唯一完全匹配后解析为 ID（元信息写入 meta_out），否则返回候选列表。"""
    if is_code_arg(raw):
        return _parse_str_list(raw) or [], None

    _require_auth()
    resolved: List[str] = []
    search_outputs: List[str] = []
    for token in _parse_str_list(raw) or []:
        records, total, part_err = _fetch_drive_list(
            keyword=token,
            max_total=limit,
            page_from=search_kwargs.get("page_from", 0),
            page_size=search_kwargs.get("page_size", 20),
            start_time=search_kwargs.get("start_time"),
            end_time=search_kwargs.get("end_time"),
            file_type_list=search_kwargs.get("file_type_list"),
            space_type_list=search_kwargs.get("space_type_list"),
        )
        if not records:
            return None, format_response(
                {"state": "error", "message": f"未找到与「{token}」相关的云盘文件", "data": [], "usage": {}},
                METHOD,
                output_dir=output_dir,
            )
        exact = _exact_match_files(token, records)
        if len(exact) == 1:
            fid = str(exact[0].get("file_id") or "").strip()
            if fid:
                resolved.append(fid)
                if meta_out is not None:
                    meta_out[fid] = exact[0]
            continue
        if len(exact) > 1:
            prefix = f"「{token}」存在 {len(exact)} 条完全匹配，请指定更精确的标题或 ID：\n\n"
            candidates = exact
        else:
            prefix = f"未找到与「{token}」完全匹配的云盘文件，以下为候选结果：\n\n"
            candidates = records
        search_outputs.append(str(_format_file_list(candidates, total, part_err, False, output_dir, prefix=prefix)))

    if search_outputs:
        return None, "\n\n".join(search_outputs)
    return resolved, None


# ---------------------------------------------------------------------------
# 查询 / 下载
# ---------------------------------------------------------------------------


def private_cloud_search(
    keyword: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    file_type_list: Optional[List[str]] = None,
    space_type_list: Optional[List[int]] = None,
    limit: int = DEFAULT_LIST_LIMIT,
    page_from: int = 0,
    page_size: int = 20,
    output_dir: Optional[str] = None,
    append_file_hint: bool = False,
):
    _require_auth()
    records, total, part_err = _fetch_drive_list(
        page_from=page_from,
        page_size=page_size,
        start_time=start_time,
        end_time=end_time,
        keyword=keyword,
        file_type_list=file_type_list,
        space_type_list=space_type_list,
        max_total=limit,
    )
    if not records:
        return format_response(
            {"state": "error", "message": part_err or "未找到云盘文件", "data": [], "usage": {}},
            METHOD,
            output_dir=output_dir,
        )
    return _format_file_list(records, total, part_err, append_file_hint, output_dir)


def private_cloud_get(
    file_ids: List[str],
    meta_by_id: Optional[Dict[str, dict]] = None,
    output_dir: Optional[str] = None,
):
    _require_auth()
    ids = [str(x).strip() for x in file_ids if str(x).strip()]
    if not ids:
        raise ValidationError("请指定 fileId：使用 --files 或先运行 search 获取列表")

    files: List[dict] = []
    errs: List[str] = []
    meta_by_id = dict(meta_by_id or {})
    missing = [fid for fid in ids if not (meta_by_id.get(fid) or {}).get("title")]
    if missing:
        meta_by_id.update(_lookup_file_meta(missing))

    for fid in ids:
        meta = meta_by_id.get(fid) or {}
        item, derr = _download_drive_file(
            fid,
            title=str(meta.get("title") or ""),
            create_time=str(meta.get("create_time") or ""),
            url=str(meta.get("url") or ""),
        )
        if derr:
            errs.append(f"{fid}: {derr}")
            continue
        if item:
            files.append(item)

    if not files:
        return format_response(
            {"state": "error", "message": "；".join(errs) if errs else "未下载到云盘文件", "data": [], "usage": {}},
            METHOD,
            output_dir=output_dir,
        )

    parts = [{"data": files, "module": "private_cloud_content", "type": "files"}]
    msg = f"已下载 {len(files)} 个云盘文件"
    if errs:
        msg += f"；部分失败：{'；'.join(errs[:3])}"
    return format_response(
        {"state": "success", "message": msg, "data": parts, "usage": {}},
        METHOD,
        output_dir=output_dir,
    )


def private_cloud_folder_list(
    space_type: int = 1,
    parent_id: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    _require_auth()
    payload: Dict[str, Any] = {"spaceType": int(space_type), "parentId": (parent_id or "root").strip() or "root"}
    data = _post(DRIVE_FOLDER_LIST_URL, payload)
    data = data if isinstance(data, dict) else {}

    folders = [
        {
            "folder_id": x.get("folderId"),
            "parent_id": x.get("parentId"),
            "folder_name": x.get("folderName"),
            "space_type": x.get("spaceType"),
            "create_time": x.get("createTime"),
        }
        for x in (data.get("folderList") or [])
        if isinstance(x, dict)
    ]
    files = [
        {
            "file_id": x.get("fileId"),
            "title": x.get("title"),
            "file_size": x.get("fileSize"),
            "create_time": x.get("createTime"),
        }
        for x in (data.get("fileList") or [])
        if isinstance(x, dict)
    ]

    location = f"spaceType={payload['spaceType']}，parentId={payload['parentId']}"
    if not folders and not files:
        return _success_message(f"该文件夹为空（{location}）", output_dir)

    parts = []
    if folders:
        parts.append({"data": folders, "module": "private_cloud_folders", "type": "data"})
    if files:
        parts.append({"data": files, "module": "private_cloud_folder_files", "type": "data"})
    msg = (
        f"{location} 下共 {data.get('folderTotal', len(folders))} 个子文件夹、"
        f"{data.get('fileTotal', len(files))} 个文件；可用 --parent-id <folder_id> 继续浏览子文件夹"
    )
    return format_response({"state": "success", "message": msg, "data": parts, "usage": {}}, METHOD, output_dir=output_dir)


# ---------------------------------------------------------------------------
# 管理操作
# ---------------------------------------------------------------------------


def _upload_one(path: str, name: str, space_type: int, folder_id: Optional[str]) -> dict:
    form: Dict[str, Any] = {"spaceType": str(int(space_type)), "title": name}
    if folder_id:
        form["folderId"] = folder_id
    with open(path, "rb") as fh:
        resp = authorized_request(
            "POST",
            DRIVE_UPLOAD_URL,
            data=form,
            files={"file": (os.path.basename(path), fh)},
            timeout=600,
        )
    try:
        body = resp.json()
    except ValueError as exc:
        raise ApiError(f"上传失败 (HTTP {resp.status_code})", http=resp.status_code, body=resp.text[:500]) from exc
    data = unwrap(body, http=resp.status_code)
    return data if isinstance(data, dict) else {}


def private_cloud_upload(
    file_paths: List[str],
    space_type: int = 1,
    folder_id: Optional[str] = None,
    title: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    _require_auth()
    paths = [str(p).strip() for p in (file_paths or []) if str(p).strip()]
    if not paths:
        raise ValidationError("upload 模式请指定 --file-paths 本地文件路径")
    if title and len(paths) > 1:
        raise ValidationError("--name 仅在上传单个文件时可用")

    problems: List[str] = []
    for path in paths:
        if not os.path.isfile(path):
            problems.append(f"{path}：本地文件不存在")
        elif os.path.getsize(path) > MAX_UPLOAD_BYTES:
            problems.append(f"{path}：文件大小超过 100MB 上限")
        elif _name_length((title or os.path.basename(path)).strip()) > MAX_NAME_LEN:
            problems.append(f"{path}：文件名超过 {MAX_NAME_LEN} 个字符")
    if problems:
        raise ValidationError("上传文件无效：" + "；".join(problems))

    if len(paths) == 1:
        data = _upload_one(paths[0], (title or os.path.basename(paths[0])).strip(), space_type, folder_id)
        return _success_message(
            f"上传成功：{paths[0]} → fileId={data.get('fileId')}，title={data.get('title')}，"
            f"folderId={data.get('folderId')}，spaceType={data.get('spaceType')}，fileSize={data.get('fileSize')}",
            output_dir,
        )

    lines: List[str] = []
    ok_count = 0
    for path in paths:
        try:
            data = _upload_one(path, os.path.basename(path), space_type, folder_id)
        except GangtiseError as e:
            lines.append(f"- {path}：上传失败，{e}")
            continue
        ok_count += 1
        lines.append(f"- {path} → fileId={data.get('fileId')}，folderId={data.get('folderId')}")

    msg = f"上传完成：成功 {ok_count} 个，失败 {len(paths) - ok_count} 个\n" + "\n".join(lines)
    if ok_count == 0:
        raise ApiError(msg)
    if ok_count < len(paths):
        raise PartialResultError(msg)
    return _success_message(msg, output_dir)


def private_cloud_create_folder(
    folder_name: str,
    space_type: int = 1,
    parent_id: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    _require_auth()
    name = (folder_name or "").strip()
    if not name:
        raise ValidationError("create_folder 模式请指定 --name 文件夹名称")
    if _name_length(name) > MAX_NAME_LEN:
        raise ValidationError(f"文件夹名称超过 {MAX_NAME_LEN} 个字符")

    payload: Dict[str, Any] = {"folderName": name, "spaceType": int(space_type)}
    if parent_id:
        payload["parentId"] = parent_id
    data = _post(DRIVE_CREATE_FOLDER_URL, payload)
    data = data if isinstance(data, dict) else {}
    return _success_message(
        f"已新建文件夹：folderId={data.get('folderId')}，folderName={data.get('folderName')}，"
        f"parentId={data.get('parentId')}，spaceType={data.get('spaceType')}，createTime={data.get('createTime')}",
        output_dir,
    )


def private_cloud_rename(
    target_type: str,
    target_id: str,
    name: str,
    output_dir: Optional[str] = None,
):
    _require_auth()
    new_name = (name or "").strip()
    if not target_id:
        raise ValidationError("rename 模式请指定 --file-ids（文件）或 --folder-id（文件夹）")
    if not new_name:
        raise ValidationError("rename 模式请指定 --name 新名称")
    if _name_length(new_name) > MAX_NAME_LEN:
        raise ValidationError(f"新名称超过 {MAX_NAME_LEN} 个字符")

    data = _post(DRIVE_RENAME_URL, {"type": target_type, "id": target_id, "name": new_name})
    data = data if isinstance(data, dict) else {}
    label = "文件夹" if target_type == "folder" else "文件"
    return _success_message(f"{label}重命名成功：id={data.get('id')}，name={data.get('name')}", output_dir)


def private_cloud_move_file(
    file_ids: List[str],
    target_folder_id: str,
    output_dir: Optional[str] = None,
):
    _require_auth()
    if not file_ids:
        raise ValidationError("move_file 模式请指定 --file-ids")
    if not target_folder_id:
        raise ValidationError("move_file 模式请指定 --target-folder-id（root 表示根目录）")

    data = _post(DRIVE_MOVE_FILE_URL, {"fileIdList": file_ids, "targetFolderId": target_folder_id})
    return _success_message(_success_lines("移动文件", data), output_dir)


def private_cloud_move_folder(
    folder_id: str,
    target_parent_id: str,
    output_dir: Optional[str] = None,
):
    _require_auth()
    if not folder_id:
        raise ValidationError("move_folder 模式请指定 --folder-id")
    if not target_parent_id:
        raise ValidationError("move_folder 模式请指定 --target-folder-id（root 表示根目录）")

    data = _post(DRIVE_MOVE_FOLDER_URL, {"folderId": folder_id, "targetParentId": target_parent_id})
    data = data if isinstance(data, dict) else {}
    return _success_message(
        f"文件夹移动成功：folderId={data.get('folderId')}，parentId={data.get('parentId')}", output_dir
    )


def private_cloud_copy(
    target_type: str,
    target_folder_id: str,
    file_ids: Optional[List[str]] = None,
    folder_id: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    _require_auth()
    if not target_folder_id:
        raise ValidationError("copy 模式请指定 --target-folder-id（须位于另一空间，root 表示另一空间根目录）")

    if target_type == "folder":
        if not folder_id:
            raise ValidationError("复制文件夹请指定 --folder-id")
        data = _post(DRIVE_COPY_URL, {"copyType": "folder", "folderId": folder_id, "targetParentId": target_folder_id})
        data = data if isinstance(data, dict) else {}
        return _success_message(
            f"文件夹复制成功：源 folderId={data.get('folderId')} → 新 folderId={data.get('newFolderId')}", output_dir
        )

    if not file_ids:
        raise ValidationError("复制文件请指定 --file-ids")
    data = _post(DRIVE_COPY_URL, {"copyType": "file", "fileIdList": file_ids, "targetFolderId": target_folder_id})
    return _success_message(_success_lines("复制文件", data), output_dir)


def private_cloud_delete_file(file_ids: List[str], output_dir: Optional[str] = None):
    _require_auth()
    if not file_ids:
        raise ValidationError("delete_file 模式请指定 --file-ids")
    data = _post(DRIVE_DELETE_FILE_URL, {"fileIdList": file_ids})
    return _success_message(_success_lines("删除文件", data), output_dir)


def private_cloud_delete_folder(folder_id: str, output_dir: Optional[str] = None):
    _require_auth()
    if not folder_id:
        raise ValidationError("delete_folder 模式请指定 --folder-id")
    if folder_id == "root":
        raise ValidationError("已拒绝：不允许删除根目录")
    data = _post(DRIVE_DELETE_FOLDER_URL, {"folderId": folder_id})
    data = data if isinstance(data, dict) else {}
    return _success_message(f"已删除文件夹（含其内全部子文件夹与文件）：folderId={data.get('folderId')}", output_dir)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def private_cloud_finder(
    mode: str = "search",
    keyword: Optional[str] = None,
    file_ids: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    file_type_list: Optional[List[str]] = None,
    space_type_list: Optional[List[str]] = None,
    limit: int = DEFAULT_LIST_LIMIT,
    page_from: int = 0,
    page_size: int = 20,
    space_type: Optional[str] = None,
    parent_id: Optional[str] = None,
    folder_id: Optional[str] = None,
    target_folder_id: Optional[str] = None,
    target_type: Optional[str] = None,
    name: Optional[str] = None,
    file_paths: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
    confirm: bool = False,
):
    """按 mode 分发到 AI 云盘各接口；mode=search 且提供 file_ids 时自动下载。"""
    mode = (mode or "search").strip()
    if mode not in MODES:
        raise ValidationError(f"mode 仅支持 {'/'.join(MODES)}，收到 {mode}")
    if mode in DELETE_WARNINGS and not confirm:
        raise ValidationError(DELETE_WARNINGS[mode])
    if target_type and target_type not in ("file", "folder"):
        raise ValidationError(f"target_type 仅支持 file/folder，收到 {target_type}")

    st: Optional[int] = None
    if space_type is not None and str(space_type).strip():
        st = _normalize_space_type(space_type)
        if st is None:
            raise ValidationError(f"space_type 仅支持 1/2 或 我的云盘/租户云盘，收到 {space_type}")

    folder_id = (folder_id or "").strip() or None
    target_folder_id = (target_folder_id or "").strip() or None
    search_kwargs = dict(
        start_time=start_time,
        end_time=end_time,
        file_type_list=_normalize_file_type_list(_parse_str_list(file_type_list)),
        space_type_list=_normalize_space_type_list(_parse_str_list(space_type_list)),
        page_from=page_from,
        page_size=page_size,
    )
    has_files = bool(file_ids and str(file_ids).strip())

    ids: List[str] = []
    meta_by_id: Dict[str, dict] = {}
    if has_files and mode in ("search", "get", "rename", "move_file", "copy", "delete_file"):
        resolved, out = _resolve_files_from_arg(
            str(file_ids).strip(), int(limit), output_dir, meta_out=meta_by_id, **search_kwargs
        )
        if out is not None:
            return out
        ids = resolved or []

    if mode in ("search", "get"):
        if ids:
            return private_cloud_get(file_ids=ids, meta_by_id=meta_by_id, output_dir=output_dir)
        if mode == "get":
            raise ValidationError("get 模式请指定 --file-ids 或 --files-file")
        return private_cloud_search(keyword=keyword, limit=int(limit), output_dir=output_dir, append_file_hint=True, **search_kwargs)

    st = st or 1
    if not target_type:
        target_type = "folder" if (folder_id and not has_files) else "file"

    if mode == "folder_list":
        return private_cloud_folder_list(space_type=st, parent_id=parent_id, output_dir=output_dir)
    if mode == "upload":
        return private_cloud_upload(_parse_str_list(file_paths) or [], space_type=st, folder_id=folder_id, title=name, output_dir=output_dir)
    if mode == "create_folder":
        return private_cloud_create_folder(name or "", space_type=st, parent_id=parent_id, output_dir=output_dir)
    if mode == "rename":
        if target_type == "file" and len(ids) > 1:
            raise ValidationError("rename 一次只能重命名一个文件")
        target_id = folder_id if target_type == "folder" else (ids[0] if ids else "")
        return private_cloud_rename(target_type, target_id or "", name or "", output_dir=output_dir)
    if mode == "move_file":
        return private_cloud_move_file(ids, target_folder_id or "", output_dir=output_dir)
    if mode == "move_folder":
        return private_cloud_move_folder(folder_id or "", target_folder_id or "", output_dir=output_dir)
    if mode == "copy":
        return private_cloud_copy(target_type, target_folder_id or "", file_ids=ids, folder_id=folder_id, output_dir=output_dir)
    if mode == "delete_file":
        return private_cloud_delete_file(ids, output_dir=output_dir)
    return private_cloud_delete_folder(folder_id or "", output_dir=output_dir)


def main():
    import argparse

    try:
        if not check_version():
            print("[WARNING] 存在 Gangtise private 版本更新，请与用户确认是否更新\n")
    except Exception:
        print("[WARNING] 检查 Gangtise private 版本失败\n")

    parser = argparse.ArgumentParser(
        description="AI云盘：检索/下载文件、浏览文件夹，以及上传、新建文件夹、重命名、移动、复制、删除（open-vault drive）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=MODES,
        default="search",
        help=(
            "search=列文件；get=下载；folder_list=浏览文件夹；upload=上传；create_folder=新建文件夹；"
            "rename=重命名；move_file/move_folder=移动；copy=跨空间复制；delete_file/delete_folder=删除。"
            "search 模式下提供 --files/--files-file 时自动为 get"
        ),
    )
    parser.add_argument("-k", "--keyword", default=None, help="文件标题关键词（search 模式）")
    parser.add_argument("-st", "--start-time", default=None, help="创建时间起（search）")
    parser.add_argument("-et", "--end-time", default=None, help="创建时间止（search）")
    parser.add_argument(
        "--file-type-list",
        default=None,
        help="文件类型（search）：document,image,media,article,other 或中文（文档/图片等）",
    )
    parser.add_argument(
        "--space-type-list",
        default=None,
        help="所属区域（search）：1/2 或 我的云盘/租户云盘，逗号分隔",
    )
    parser.add_argument(
        "--files",
        "--file-ids",
        dest="files",
        default=None,
        help=(
            "文件 ID 或标题，逗号分隔；纯字母数字视为 ID，否则 search 唯一完全匹配时解析为 ID。"
            "用于 get/rename/move_file/copy/delete_file"
        ),
    )
    parser.add_argument("--files-file", default=None, help="csv 含 file_id 列，等价于 --files")
    parser.add_argument("-l", "--limit", type=int, default=DEFAULT_LIST_LIMIT, help="search 模式列表条数上限")
    parser.add_argument("--page-from", type=int, default=0)
    parser.add_argument("--page-size", type=int, default=20, help="单页最大 50")
    parser.add_argument(
        "--space-type",
        default=None,
        help="单个所属区域：1/2 或 我的云盘/租户云盘（folder_list/upload/create_folder，默认 1）",
    )
    parser.add_argument("--parent-id", default=None, help="父文件夹 ID，root 或不传为根目录（folder_list/create_folder）")
    parser.add_argument(
        "--folder-id",
        default=None,
        help="文件夹 ID：upload 的目标文件夹；rename/move_folder/copy/delete_folder 的源文件夹",
    )
    parser.add_argument(
        "--target-folder-id",
        default=None,
        help="目标文件夹 ID，root 为根目录（move_file/move_folder/copy；copy 须位于另一空间）",
    )
    parser.add_argument(
        "--target-type",
        choices=["file", "folder"],
        default=None,
        help="rename/copy 的对象类型；不传时按是否提供 --files / --folder-id 自动判断",
    )
    parser.add_argument("--name", default=None, help="名称：create_folder 的文件夹名；rename 的新名称；upload 的文件名（单文件）")
    parser.add_argument("--file-path", "--file-paths", dest="file_path", nargs="+", default=None, help="本地文件路径，可多个（upload）")
    parser.add_argument("-od", "--output-dir", default=None, help="结果保存目录路径（GTS_SAVE_FILE=True）")
    parser.add_argument("--yes", "--confirm", dest="confirm", action="store_true", help="确认删除（delete_file/delete_folder 必填；不可恢复，须先取得用户同意）")

    args = parser.parse_args()

    file_ids_arg = args.files
    if args.files_file:
        try:
            file_ids_arg = ",".join(_load_file_ids_from_file(args.files_file))
        except Exception as e:
            print(f"读取 file_id 文件失败: {e}")
            sys.exit(1)

    print(
        private_cloud_finder(
            mode=args.mode,
            keyword=args.keyword,
            file_ids=file_ids_arg,
            start_time=args.start_time,
            end_time=args.end_time,
            file_type_list=_parse_str_list(args.file_type_list),
            space_type_list=_parse_str_list(args.space_type_list),
            limit=int(args.limit),
            page_from=args.page_from,
            page_size=args.page_size,
            space_type=args.space_type,
            parent_id=args.parent_id,
            folder_id=args.folder_id,
            target_folder_id=args.target_folder_id,
            target_type=args.target_type,
            name=args.name,
            file_paths=args.file_path,
            output_dir=args.output_dir,
            confirm=bool(args.confirm),
        )
    )


if __name__ == "__main__":
    encoding = "utf-8"
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding=encoding, errors="ignore")
    main()
