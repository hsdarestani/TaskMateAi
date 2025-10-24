from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, MutableMapping


class WorkspaceStorage:
    """Persist user workspace mapping on disk."""

    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = Path(__file__).resolve().parent.parent / "data" / "user_workspaces.json"
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Dict[str, str]]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def save(self, mapping: MutableMapping[str, Dict[str, str]]) -> None:
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(mapping, fh, ensure_ascii=False, indent=2)

