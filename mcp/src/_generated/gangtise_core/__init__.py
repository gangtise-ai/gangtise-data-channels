# GENERATED FILE. Do not edit. Source: core/src/gangtise_core/__init__.py
# Regenerate: python3 scripts/generate.py
"""Shared Gangtise runtime: envelope, auth, Result, renderers.

This package is the editable source under `core/src/gangtise_core`.
Copies under `*/_generated/gangtise_core` are produced by `scripts/generate.py`.
"""

from .auth import (
    authorized_request,
    clear_credentials,
    gangtise_domain,
    get_authorization_headers,
    get_authorization_path,
    get_authorization_token,
    get_headers_extra,
    invalidate_authorization,
    is_auth_configured,
    refresh_authorization,
    save_credentials,
)
from .bootstrap import ensure_core_on_path, register_scripts_package, relaunch
from .envelope import unwrap
from .errors import ApiError, GangtiseError, PartialResultError, StructuralError, ValidationError
from .format import emit_cli, invoke_legacy, render_mcp_text, render_skill
from .result import Result, SavedFile
from .timeutil import maybe_timestamp13, parse_date_option, parse_datetime_option, to_timestamp13
from .ziprow import zip_field_row, zip_field_rows

__all__ = [
    "ApiError",
    "GangtiseError",
    "PartialResultError",
    "Result",
    "SavedFile",
    "StructuralError",
    "ValidationError",
    "parse_date_option",
    "parse_datetime_option",
    "authorized_request",
    "clear_credentials",
    "emit_cli",
    "ensure_core_on_path",
    "gangtise_domain",
    "get_authorization_headers",
    "get_authorization_path",
    "get_authorization_token",
    "get_headers_extra",
    "invalidate_authorization",
    "invoke_legacy",
    "is_auth_configured",
    "maybe_timestamp13",
    "refresh_authorization",
    "register_scripts_package",
    "relaunch",
    "render_mcp_text",
    "render_skill",
    "save_credentials",
    "to_timestamp13",
    "unwrap",
    "zip_field_row",
    "zip_field_rows",
]
