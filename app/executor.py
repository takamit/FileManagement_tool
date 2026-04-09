from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


class BackupManager:
    def __init__(self, backup_root: str = "backup") -> None:
        self.backup_root = Path(backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def start_session(self) -> dict[str, Any]:
        session_dir = self.backup_root / "session_latest"
        session_dir.mkdir(parents=True, exist_ok=True)
        return {"session_dir": str(session_dir), "entries": []}

    def backup_file(self, session: dict[str, Any], target_path: str) -> str:
        target = Path(target_path)
        session_dir = Path(session["session_dir"])
        backup_path = session_dir / target.name
        shutil.copy2(target, backup_path)
        return str(backup_path)

    def add_entry(self, session: dict[str, Any], entry: dict[str, Any]) -> None:
        session["entries"].append(entry)
        manifest = Path(session["session_dir"]) / "manifest.json"
        manifest.write_text(
            json.dumps(session["entries"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def move_replace_with_backup(
    source_path: str,
    target_path: str,
    backup_manager: BackupManager,
    session: dict[str, Any],
) -> str:
    source = Path(source_path)
    target = Path(target_path)

    if not source.exists():
        raise FileNotFoundError(f"更新元が見つかりません: {source_path}")
    if not target.exists():
        raise FileNotFoundError(f"更新先が見つかりません: {target_path}")

    backup_path = backup_manager.backup_file(session, target_path)
    backup = Path(backup_path)

    try:
        target.unlink()
    except Exception as e:
        raise RuntimeError(f"更新先ファイルを削除できませんでした: {e}") from e

    try:
        shutil.move(str(source), str(target))
    except Exception as e:
        try:
            if backup.exists() and not target.exists():
                shutil.copy2(str(backup), str(target))
        except Exception as restore_error:
            raise RuntimeError(
                "ファイル移動による更新に失敗し、バックアップ復元にも失敗しました: "
                f"{e} / restore: {restore_error}"
            ) from restore_error
        raise RuntimeError(
            f"ファイル移動による更新に失敗しましたが、バックアップから復元しました: {e}"
        ) from e

    backup_manager.add_entry(
        session,
        {
            "operation": "update",
            "target_path": target_path,
            "backup_path": backup_path,
            "source_original_path": source_path,
        },
    )
    return backup_path
