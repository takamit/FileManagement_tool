from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import shutil
from typing import Any


class BackupManager:
    def __init__(self, base_dir: str, max_sessions: int = 50) -> None:
        self.root = Path(base_dir) / "backup"
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "sessions_index.json"
        self.max_sessions = max(1, int(max_sessions))

    def _load_index(self) -> list[dict]:
        if not self.index_path.exists():
            return []
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        return data if isinstance(data, list) else []

    def _save_index(self, data: list[dict]) -> None:
        self.index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def start_session(self, metadata: dict[str, Any] | None = None) -> dict:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        session_dir = self.root / stamp
        suffix = 1
        while session_dir.exists():
            session_dir = self.root / f"{stamp}_{suffix}"
            suffix += 1
        session_dir.mkdir(parents=True, exist_ok=True)
        return {
            "stamp": session_dir.name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "session_dir": str(session_dir),
            "entries": [],
            "metadata": metadata or {},
        }

    def backup_file(self, session: dict, file_path: str) -> str:
        src = Path(file_path)
        session_dir = Path(session["session_dir"])
        dst = session_dir / src.name
        i = 1
        while dst.exists():
            dst = session_dir / f"{src.stem}_{i}{src.suffix}"
            i += 1
        shutil.copy2(str(src), str(dst))
        return str(dst)

    def add_entry(self, session: dict, entry: dict) -> None:
        session.setdefault("entries", []).append(entry)

    def _build_index_entry(self, session: dict, manifest_path: str) -> dict:
        entries = session.get("entries", [])
        counter = Counter(entry.get("operation", "unknown") for entry in entries)
        return {
            "created_at": session.get("created_at", ""),
            "stamp": session.get("stamp", ""),
            "entry_count": len(entries),
            "manifest_path": manifest_path,
            "metadata": session.get("metadata", {}),
            "operations": dict(counter),
        }

    def finalize(self, session: dict) -> str:
        manifest_path = Path(session["session_dir"]) / "manifest.json"
        manifest_path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
        index = self._load_index()
        index.insert(0, self._build_index_entry(session, str(manifest_path)))
        self._save_index(index[: self.max_sessions])
        return str(manifest_path)

    def list_recent_sessions(self, limit: int | None = 3) -> list[dict]:
        rows = self._load_index()
        return rows if limit is None else rows[: max(0, int(limit))]

    def read_manifest(self, manifest_path: str) -> dict:
        path = Path(manifest_path)
        if not path.exists():
            raise FileNotFoundError(f"指定されたバックアップ情報が見つかりません: {manifest_path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("バックアップ情報の形式が不正です。")
        return data

    def describe_session(self, manifest_or_path: str | dict) -> dict:
        manifest = self.read_manifest(manifest_or_path) if isinstance(manifest_or_path, str) else manifest_or_path
        entries = manifest.get("entries", [])
        counter = Counter(entry.get("operation", "unknown") for entry in entries)
        preview_rows = []
        for idx, entry in enumerate(entries, start=1):
            preview_rows.append(
                {
                    "no": idx,
                    "operation": entry.get("operation", ""),
                    "target_path": entry.get("target_path", ""),
                    "source_original_path": entry.get("source_original_path", ""),
                    "backup_path": entry.get("backup_path", ""),
                }
            )
        return {
            "stamp": manifest.get("stamp", ""),
            "created_at": manifest.get("created_at", ""),
            "session_dir": manifest.get("session_dir", ""),
            "entry_count": len(entries),
            "operations": dict(counter),
            "metadata": manifest.get("metadata", {}),
            "entries": preview_rows,
        }

    def undo_session(self, manifest_path: str) -> tuple[int, int, list[str]]:
        try:
            manifest = self.read_manifest(manifest_path)
        except Exception as exc:
            return 0, 1, [str(exc)]

        success = 0
        failed = 0
        messages: list[str] = []
        for entry in reversed(manifest.get("entries", [])):
            try:
                op = entry.get("operation")
                target_path = Path(entry.get("target_path", ""))
                backup_path = Path(entry.get("backup_path", ""))
                source_original_path = Path(entry.get("source_original_path", "")) if entry.get("source_original_path") else Path()

                if op == "trash":
                    if not backup_path.exists():
                        failed += 1
                        messages.append(f"戻せませんでした: {target_path}（バックアップなし）")
                        continue
                    if target_path.exists():
                        failed += 1
                        messages.append(f"戻せませんでした: {target_path}（既に同名ファイルあり）")
                        continue
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(backup_path), str(target_path))
                    success += 1
                    messages.append(f"戻しました: {target_path}")
                    continue

                if op == "update_copy":
                    if not backup_path.exists():
                        failed += 1
                        messages.append(f"戻せませんでした: {target_path}（バックアップなし）")
                        continue
                    if target_path.exists():
                        try:
                            target_path.unlink()
                        except Exception as exc:
                            failed += 1
                            messages.append(f"戻せませんでした: {target_path}（現在ファイル削除失敗: {exc}）")
                            continue
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(backup_path), str(target_path))
                    success += 1
                    messages.append(f"コピー更新前の状態に戻しました: {target_path}")
                    continue

                if op == "update_move":
                    current_target_file = target_path
                    if current_target_file.exists() and str(source_original_path):
                        if source_original_path.exists():
                            failed += 1
                            messages.append(f"戻せませんでした: {source_original_path}（元の場所に既に同名ファイルあり）")
                            continue
                        source_original_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(current_target_file), str(source_original_path))
                    elif current_target_file.exists():
                        current_target_file.unlink()

                    if not backup_path.exists():
                        failed += 1
                        messages.append(f"戻せませんでした: {target_path}（バックアップなし）")
                        continue

                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(backup_path), str(target_path))
                    success += 1
                    messages.append(f"移動更新前の状態に戻しました: {target_path}")
                    continue

                failed += 1
                messages.append(f"戻せませんでした: {target_path}（未対応操作: {op}）")
            except Exception as exc:
                failed += 1
                messages.append(f"戻せませんでした: {entry.get('target_path', '')} ({exc})")
        return success, failed, messages
