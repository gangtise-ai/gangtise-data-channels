"""附件路径收紧，以及结果文件不再按秒重名。"""
import base64
import datetime
import io
import os
import sys
import uuid
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("mcp")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp" / "src"))

import result_attachments as ra  # noqa: E402


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("WORK_PATH", str(tmp_path))
    monkeypatch.setenv("DEPLOY_ENV", "test")
    monkeypatch.setenv("MCP_CLEANUP_LOCAL_AFTER_ATTACH", "false")
    monkeypatch.delenv("GTS_WORK_PATH", raising=False)
    return tmp_path


def test_slash_dot_fragment_is_not_zipped_as_root(workspace):
    text = "观点摘要 /. 详见附件"
    body, attachments = ra.build_path_attachments(text)
    assert body == text
    assert attachments == []
    assert "准备失败" not in body
    assert "trigger_fs_error" not in body


def test_path_outside_workspace_is_left_alone(workspace, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "note.txt"
    outside.write_text("secret", encoding="utf-8")
    text = f"正文提到 {outside}"
    body, attachments = ra.build_path_attachments(text)
    assert body == text
    assert attachments == []


def test_workspace_file_still_attaches(workspace):
    path = workspace / "opinion.md"
    path.write_text("hello", encoding="utf-8")
    body, attachments = ra.build_path_attachments(f"已保存 `{path}`")
    assert "附件: `opinion.md`" in body
    assert "暂不可用" not in body
    assert len(attachments) == 1
    blob = base64.b64decode(attachments[0].resource.blob)
    assert blob == b"hello"


def test_prepare_failure_does_not_leak_errno(workspace, monkeypatch):
    path = workspace / "a.txt"
    path.write_text("x", encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise PermissionError(13, "Permission denied", "/sys/fs/ext4/dm-0/trigger_fs_error")

    monkeypatch.setattr(ra, "_read_file_attachment", boom)
    body, attachments = ra.build_path_attachments(f"已保存 `{path}`")
    assert attachments == []
    assert "暂不可用" in body
    assert "Errno" not in body
    assert "trigger_fs_error" not in body
    assert "Permission denied" not in body


def test_directory_skips_symlink_outside_workspace(workspace):
    folder = workspace / "pack"
    folder.mkdir()
    (folder / "keep.txt").write_text("keep", encoding="utf-8")
    outside = workspace.parent / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")
    (folder / "leak").symlink_to(outside)
    body, attachments = ra.build_path_attachments(f"目录 `{folder}`")
    assert "暂不可用" not in body
    assert len(attachments) == 1
    blob = base64.b64decode(attachments[0].resource.blob)
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = zf.namelist()
        assert any(name.endswith("keep.txt") for name in names)
        assert all("leak" not in name and "secret" not in name for name in names)
        assert b"secret" not in b"".join(zf.read(name) for name in names)


def test_result_filenames_include_date_and_do_not_collide():
    root = Path(__file__).resolve().parents[1] / "skills" / "openapi"
    utils_files = list(root.glob("*/scripts/utils.py"))
    assert utils_files
    for path in utils_files:
        text = path.read_text(encoding="utf-8")
        assert "文件存储系统繁忙" not in text, path
        assert "max_retries = 10" not in text, path
        assert "def _unique_result_path" in text, path

    sample = (root / "gangtise-file" / "scripts" / "utils.py").read_text(encoding="utf-8")
    start = sample.index("def _unique_result_path")
    end = sample.index("\ndef format_response")
    namespace = {"os": os, "datetime": datetime, "uuid": uuid}
    exec(sample[start:end], namespace)
    dest = Path(os.environ.get("TMPDIR", "/tmp")) / f"gts-name-{uuid.uuid4().hex}"
    dest.mkdir()
    try:
        first = namespace["_unique_result_path"](str(dest), "opinion", "md")
        second = namespace["_unique_result_path"](str(dest), "opinion", "md")
        assert first != second
        assert os.path.basename(first).startswith("opinion_")
        assert os.path.basename(first).count("_") >= 3
        assert first.endswith(".md")
    finally:
        for child in dest.iterdir():
            child.unlink()
        dest.rmdir()
