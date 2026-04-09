from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str, default: Any) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path: str, data: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_settings(path: str = "config/settings.json") -> dict[str, Any]:
    return load_json(path, {})


def save_settings(data: dict[str, Any], path: str = "config/settings.json") -> None:
    save_json(path, data)
