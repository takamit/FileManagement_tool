from __future__ import annotations

from pathlib import Path

from core.backup_manager import BackupManager


def test_describe_session_contains_operation_summary(tmp_path: Path) -> None:
    manager = BackupManager(str(tmp_path), max_sessions=20)
    source = tmp_path / "a.txt"
    source.write_text("x", encoding="utf-8")
    session = manager.start_session(metadata={"dry_run": False})
    backup_path = manager.backup_file(session, str(source))
    manager.add_entry(
        session,
        {
            "operation": "trash",
            "target_path": str(source),
            "backup_path": backup_path,
        },
    )
    manifest_path = manager.finalize(session)
    details = manager.describe_session(manifest_path)
    assert details["entry_count"] == 1
    assert details["operations"]["trash"] == 1
    assert details["metadata"]["dry_run"] is False
