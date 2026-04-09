from __future__ import annotations

from typing import Callable, Iterable

from core.services.backup_manager import BackupManager
from core.services.executor import execute_items as execute_items_service
from core.services.scanner import ScanItem, scan_folders as scan_folders_service
from core.utils.runtime_control import OperationController


def scan_folders(*args, **kwargs):
    return scan_folders_service(*args, **kwargs)


def execute_items(
    items: Iterable,
    backup_manager: BackupManager,
    controller: OperationController,
    progress_cb: Callable[[int, int, str], None] | None = None,
):
    return execute_items_service(
        items=items,
        backup_manager=backup_manager,
        controller=controller,
        progress_cb=progress_cb,
    )
