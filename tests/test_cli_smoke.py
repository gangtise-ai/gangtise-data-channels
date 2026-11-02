import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cli_version_flag():
    from gangtise_cli.main import _package_version

    assert _package_version()


def test_generate_check():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr or r.stdout
