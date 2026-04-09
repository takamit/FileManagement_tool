from __future__ import annotations

from pathlib import Path


class PathValidationError(ValueError):
    """パス検証エラー。"""


def validate_existing_directory(path_value: str, label: str) -> Path:
    path = Path(path_value).expanduser().resolve()
    if not path.exists():
        raise PathValidationError(f"{label}が存在しません: {path}")
    if not path.is_dir():
        raise PathValidationError(f"{label}がフォルダではありません: {path}")
    return path
