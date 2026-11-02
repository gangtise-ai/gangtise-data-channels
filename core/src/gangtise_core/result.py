"""Channel-agnostic handler return value. Adapters render it."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .errors import ApiError, GangtiseError, PartialResultError


@dataclass
class SavedFile:
    path: str
    kind: str = "data"  # data | markdown | binary
    label: str = ""


@dataclass
class Result:
    ok: bool = True
    text: str = ""
    data: Any = None
    files: List[SavedFile] = field(default_factory=list)
    markers: Dict[str, str] = field(default_factory=dict)
    usage: Dict[str, Any] = field(default_factory=dict)
    error: Optional[GangtiseError] = None
    exit_code: int = 0
    tool: str = ""

    @classmethod
    def success(
        cls,
        text: str = "",
        *,
        data: Any = None,
        files: Optional[List[SavedFile]] = None,
        markers: Optional[Dict[str, str]] = None,
        usage: Optional[Dict[str, Any]] = None,
        tool: str = "",
    ) -> "Result":
        return cls(
            ok=True,
            text=text,
            data=data,
            files=list(files or []),
            markers=dict(markers or {}),
            usage=dict(usage or {}),
            exit_code=0,
            tool=tool,
        )

    @classmethod
    def from_error(cls, err: BaseException, *, tool: str = "") -> "Result":
        if isinstance(err, GangtiseError):
            return cls(
                ok=False,
                text=str(err),
                error=err,
                exit_code=getattr(err, "exit_code", 1),
                tool=tool,
            )
        wrapped = ApiError(str(err) or err.__class__.__name__)
        return cls(ok=False, text=str(wrapped), error=wrapped, exit_code=1, tool=tool)

    @classmethod
    def from_legacy(cls, value: Any, *, tool: str = "") -> "Result":
        """Wrap pre-refactor handler returns (Markdown string / None)."""
        if isinstance(value, Result):
            return value
        if value is None:
            return cls.success(tool=tool)
        text = value if isinstance(value, str) else str(value)
        return cls.success(text=text, tool=tool)

    def raise_if_error(self) -> "Result":
        if self.error is not None:
            raise self.error
        if not self.ok:
            raise ApiError(self.text or "handler failed")
        return self

    def __str__(self) -> str:
        if self.ok:
            return self.text or ""
        return self.text or str(self.error or "")
