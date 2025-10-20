from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HTML:  # pragma: no cover - testing stub
    string: str | None = None
    base_url: str | None = None

    def write_pdf(self, *args: Any, **kwargs: Any) -> bytes:
        return b""
