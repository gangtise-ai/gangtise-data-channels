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
import sys
from io import TextIOWrapper

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from .utils import REGIONS_MAP, check_version  # noqa: E402


def main():
    try:
        if not check_version():
            print(f"[WARNING] 存在 Gangtise skills 版本更新，请与用户确认是否更新\n")
    except Exception as e:
        print(f"[WARNING] 检查 Gangtise skills 版本失败\n")
    print(", ".join(REGIONS_MAP.keys()))


if __name__ == "__main__":
    encoding = "utf-8"
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding=encoding, errors='ignore')
    main()
