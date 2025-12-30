from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ConfigPaths:
    path: Path


class ConfigService:
    def __init__(self, paths: ConfigPaths | None = None) -> None:
        self.paths = paths or ConfigPaths(path=self.default_path())

    @staticmethod
    def default_path() -> Path:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            base = Path(xdg)
        else:
            base = Path.home() / ".config"
        return base / "ops_toolkit_gui" / "config.json"

    def load(self) -> dict[str, Any]:
        p = self.paths.path
        if not p.exists():
            return {}
        try:
            with open(p, "r", encoding="utf-8") as f:
                obj = json.load(f)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    def save(self, cfg: dict[str, Any]) -> None:
        p = self.paths.path
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2, sort_keys=True)
        tmp.replace(p)
