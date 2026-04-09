from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.logic.file_manager_logic import scan_folders
from core.executor import execute_items, export_preview_report, preview_items
from core.backup_manager import BackupManager
from core.utils.runtime_control import OperationController


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

    def preview(self, request: CliScanRequest) -> list[dict]:
        items, _ = self.scan(request)
        return preview_items(items)

    def export_preview(self, request: CliScanRequest, output_path: str, format_hint: str | None = None) -> str:
        items, _ = self.scan(request)
        return export_preview_report(items, output_path=output_path, format_hint=format_hint)

    def apply(self, request: CliScanRequest, base_dir: str, dry_run: bool = False) -> tuple[list[dict], str]:
        items, _ = self.scan(request)
        backup_manager = BackupManager(base_dir=base_dir)
        controller = OperationController()
        return execute_items(items, backup_manager=backup_manager, controller=controller, dry_run=dry_run)
