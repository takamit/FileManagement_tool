from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.logic.file_manager_logic import scan_folders


@dataclass(slots=True)
class CliScanRequest:
    source_dir: str
    compare_dir: str = ""
    exclude_dirs: list[str] | None = None
    exclude_exts: list[str] | None = None


class CliController:
    def scan(self, request: CliScanRequest) -> tuple[list, dict]:
        items, summary = scan_folders(
            source_dir=request.source_dir,
            compare_dir=request.compare_dir,
            exclude_dirs=request.exclude_dirs or [],
            exclude_exts=request.exclude_exts or [],
            progress_cb=None,
        )
        return items, summary
