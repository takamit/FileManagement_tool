from __future__ import annotations
from pathlib import Path
from typing import Callable, Iterable
import shutil
import os
from send2trash import send2trash
from .backup_manager import BackupManager
from .runtime_control import OperationController

def resolve_action(item) -> tuple[str, str]:
    if item.target_selected and item.compare_selected:
        raise ValueError("対象フォルダ側と比較フォルダ側の両方が選択されています。")
    if not item.target_selected and not item.compare_selected:
        raise ValueError("対象フォルダ側または比較フォルダ側のどちらかを選択してください。")
    if item.preferred_action == "何もしない":
        return "noop", ""
    if item.preferred_action == "選択側のファイルをゴミ箱へ移動":
        return ("trash_target", item.target_path) if item.target_selected else ("trash_compare", item.compare_path)
    if item.preferred_action in ("選択側のファイルで更新", "選択側のファイルで更新（移動）"):
        return ("update_compare_with_target", item.compare_path) if item.target_selected else ("update_target_with_compare", item.target_path)
    raise ValueError(f"未対応の処理です: {item.preferred_action}")

def _trash_with_backup(file_path: str, backup_manager: BackupManager, session: dict) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"移動対象が見つかりません: {file_path}")
    backup_path = backup_manager.backup_file(session, file_path)
    send2trash(str(path))
    backup_manager.add_entry(session, {"operation": "trash", "target_path": file_path, "backup_path": backup_path})
    return backup_path

def _move_replace_with_backup(source_path: str, target_path: str, backup_manager: BackupManager, session: dict) -> str:
    source = Path(source_path)
    target = Path(target_path)
    if not source.exists():
        raise FileNotFoundError(f"更新元が見つかりません: {source_path}")
    if not target.exists():
        raise FileNotFoundError(f"更新先が見つかりません: {target_path}")

    backup_path = backup_manager.backup_file(session, target_path)

    try:
        target.unlink()
    except Exception as e:
        raise RuntimeError(f"更新先ファイルを置き換えられませんでした: {e}")

    try:
        shutil.move(str(source), str(target))
    except Exception as e:
        raise RuntimeError(f"ファイル移動による更新に失敗しました: {e}")

    backup_manager.add_entry(session, {
        "operation": "update",
        "target_path": target_path,
        "backup_path": backup_path,
        "source_original_path": source_path,
    })
    return backup_path

def execute_items(items: Iterable, backup_manager: BackupManager, controller: OperationController,
                  progress_cb: Callable[[int, int, str], None] | None = None) -> tuple[list[dict], str]:
    items = list(items)
    total = len(items)
    results: list[dict] = []
    session = backup_manager.start_session()

    for idx, item in enumerate(items, start=1):
        controller.check()
        if progress_cb and (idx == 1 or idx == total or idx % 20 == 0):
            progress_cb(idx, total, f"実行中: {Path(item.target_path).name}")
        try:
            operation, _ = resolve_action(item)
            if operation == "noop":
                results.append({"status": "成功", "kind": "スキップ", "target": item.target_path, "action": item.preferred_action, "message": "処理なし"})
            elif operation == "trash_target":
                backup = _trash_with_backup(item.target_path, backup_manager, session)
                results.append({"status": "成功", "kind": "削除", "target": item.target_path, "action": item.preferred_action, "backup_path": backup, "message": "対象フォルダ側ファイルをゴミ箱へ移動しました"})
            elif operation == "trash_compare":
                backup = _trash_with_backup(item.compare_path, backup_manager, session)
                results.append({"status": "成功", "kind": "削除", "target": item.compare_path, "action": item.preferred_action, "backup_path": backup, "message": "比較フォルダ側ファイルをゴミ箱へ移動しました"})
            elif operation == "update_compare_with_target":
                backup = _move_replace_with_backup(item.target_path, item.compare_path, backup_manager, session)
                results.append({"status": "成功", "kind": "更新", "target": item.compare_path, "action": item.preferred_action, "source_used": item.target_path, "backup_path": backup, "message": "対象側ファイルを比較側へ移動して更新しました（更新後、対象側からは消えます）"})
            elif operation == "update_target_with_compare":
                backup = _move_replace_with_backup(item.compare_path, item.target_path, backup_manager, session)
                results.append({"status": "成功", "kind": "更新", "target": item.target_path, "action": item.preferred_action, "source_used": item.compare_path, "backup_path": backup, "message": "比較側ファイルを対象側へ移動して更新しました（更新後、比較側からは消えます）"})
            else:
                raise ValueError(f"未対応の内部処理です: {operation}")
        except InterruptedError:
            results.append({"status": "停止", "kind": "停止", "target": getattr(item, "target_path", ""), "action": getattr(item, "preferred_action", ""), "error": "処理は停止されました。"})
            break
        except Exception as e:
            results.append({"status": "失敗", "kind": "エラー", "target": getattr(item, "target_path", ""), "action": getattr(item, "preferred_action", ""), "error": str(e)})
    manifest_path = backup_manager.finalize(session)
    return results, manifest_path
