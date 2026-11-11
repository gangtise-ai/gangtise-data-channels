# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-data/scripts/block_constituents.py
# Regenerate: python3 scripts/generate.py
if __name__ == "__main__" and not __package__:
    import importlib.util
    from pathlib import Path as _P
    _launch = _P(__file__).resolve().parent / "_launch.py"
    _spec = importlib.util.spec_from_file_location("_gts_skill_launch", _launch)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(_mod)
    raise SystemExit(_mod.relaunch(__file__))

"""兼容旧入口：转发到 constituents（默认板块模式）。"""

from .constituents import (  # noqa: F401
    block_constituents_data,
    constituents_data,
    main,
)

if __name__ == "__main__":
    main()
