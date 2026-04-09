from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class ScanItem:
    path: str
    size: int
    suffix: str


def iter_files(root: str) -> Iterable[ScanItem]:
    root_path = Path(root)
    for path in root_path.rglob("*"):
        if path.is_file():
            yield ScanItem(
                path=str(path),
                size=path.stat().st_size,
                suffix=path.suffix.lower(),
            )


def scan_folder(root: str) -> list[ScanItem]:
    return list(iter_files(root))


def classify_pair(target_size: int, compare_size: int) -> str:
    if target_size == compare_size:
        return "同名同サイズ"
    if target_size > compare_size:
        return "対象側が大きい"
    return "比較側が大きい"
