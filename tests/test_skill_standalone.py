import ast
import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_skills  # noqa: E402

DATA_SCRIPTS = ROOT / "skills" / "openapi" / "gangtise-data" / "scripts"


def test_skill_checks_pass():
    assert check_skills.run_checks() == []


def test_undefined_name_check_catches_missing_import(tmp_path, monkeypatch):
    scripts = tmp_path / "gangtise-x" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "broken.py").write_text(
        "from .utils import FOO\n\ndef run():\n    return authorized_request('GET', FOO)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(check_skills, "ROOT", tmp_path)
    errors = check_skills.check_undefined([tmp_path / "gangtise-x"])
    assert errors == ["gangtise-x/scripts/broken.py:4 undefined name authorized_request"]


def test_skill_script_runs_without_gangtise_core():
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    code = (
        "import sys, runpy\n"
        f"sys.argv = [{str(DATA_SCRIPTS / 'valuation.py')!r}, '--help']\n"
        "try:\n"
        f"    runpy.run_path({str(DATA_SCRIPTS / 'valuation.py')!r}, run_name='__main__')\n"
        "except SystemExit:\n"
        "    pass\n"
        "assert not any(m.startswith('gangtise_core') for m in sys.modules), 'gangtise_core was imported'\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT.parent), env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "usage:" in proc.stdout


def _load_skill_runtime():
    spec = importlib.util.spec_from_file_location("_skill_launch_test", DATA_SCRIPTS / "_launch.py")
    launch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launch)
    pkg = launch._register_package(DATA_SCRIPTS)
    return pkg, importlib.import_module(f"{pkg}.gts_runtime")


def _response(status, body):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {}
    resp.json.return_value = body
    return resp


def test_skill_runtime_no_replay_endpoint_does_not_retry_5xx():
    pkg, runtime = _load_skill_runtime()
    bad = _response(502, {"code": "999999", "msg": "bad gateway"})
    with patch(f"{pkg}.gts_runtime.authorized_request", return_value=bad) as mocked:
        with pytest.raises(runtime.ApiError):
            runtime.request_json("POST", "https://x/application/open-vault/drive/uploadFile", json={})
    assert mocked.call_count == 1


def test_skill_runtime_default_endpoint_retries_999999():
    pkg, runtime = _load_skill_runtime()
    bad = _response(200, {"code": "999999", "msg": "busy"})
    ok = _response(200, {"code": "000000", "data": {"list": []}})
    with patch(f"{pkg}.gts_runtime.authorized_request", side_effect=[bad, ok]) as mocked:
        with patch(f"{pkg}.gts_runtime.time.sleep"):
            assert runtime.request_json("POST", "https://x/application/open-quote/kline/daily", json={}) == {"list": []}
    assert mocked.call_count == 2


def test_skill_runtime_fail_list_is_partial():
    pkg, runtime = _load_skill_runtime()
    resp = _response(200, {"code": "000000", "data": {"failList": [{"fileId": 1}]}})
    with patch(f"{pkg}.gts_runtime.authorized_request", return_value=resp):
        with pytest.raises(runtime.PartialResultError):
            runtime.request_json("POST", "https://x/application/open-vault/drive/deleteFile", json={})


def test_skill_auth_reuses_token_refreshed_elsewhere(tmp_path, monkeypatch):
    pkg, _ = _load_skill_runtime()
    auth = importlib.import_module(f"{pkg}.gts_auth")
    monkeypatch.setenv("GTS_ACCESS_KEY", "ak")
    monkeypatch.setenv("GTS_SECRET_KEY", "sk")
    monkeypatch.setenv("GTS_TOKEN_CACHE_PATH", str(tmp_path / "token.json"))
    for key in ("GTS_AUTHORIZATION", "AUTHORIZATION", "GANGTISE_AUTH_DOMAIN"):
        monkeypatch.delenv(key, raising=False)
    auth.invalidate_authorization()
    logins = iter(
        [
            {"authorization": "Bearer t1", "expires_at": 9e12},
            {"authorization": "Bearer t2", "expires_at": 9e12},
        ]
    )
    expired = _response(200, {"code": "8000014", "msg": "token expired"})
    ok = _response(200, {"code": "000000", "data": {}})
    with patch.object(auth, "_login", side_effect=lambda ak, sk: next(logins)) as login:
        with patch.object(auth.requests, "request", side_effect=[expired, ok]) as sent:
            assert auth.authorized_request("POST", "https://x/y", json={}) is ok
    assert login.call_count == 2
    assert sent.call_args_list[1].kwargs["headers"]["Authorization"] == "Bearer t2"
    auth.invalidate_authorization()


def test_generated_handlers_import_core_not_skill_copies():
    handlers = ROOT / "cli" / "src" / "_generated" / "handlers"
    assert not list(handlers.glob("*/gts_auth.py"))
    assert not list(handlers.glob("*/gts_runtime.py"))
    for path in handlers.glob("*/*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module not in {"gts_auth", "gts_runtime"}, f"{path}: relative skill import left behind"
