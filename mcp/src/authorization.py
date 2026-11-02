"""Shim: MCP 运行时继续 `from authorization import …`，实现在 gangtise_core."""
from gangtise_core.auth import *  # noqa: F403
from gangtise_core.auth import AUTHORIZATION_URL, _login  # noqa: F401
