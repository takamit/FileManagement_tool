from __future__ import annotations
import json
import shutil
from pathlib import Path
from datetime import datetime

class BackupManager:
    def __init__(self, base_dir: str) -> None:
        self.root = Path(base_dir) / "backup"
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "sessions_index.json"

    def _load_index(self) -> list[dict]:
        if not self.index_path.exists():
            return []
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_index(self, data: list[dict]) -> None:
        self.index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def start_session(self) -> dict:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        session_dir = self.root / stamp
        session_dir.mkdir(parents=True, exist_ok=True)
        return {
            "stamp": stamp,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "session_dir": str(session_dir),
            "entries": [],
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
        session["entries"].append(entry)

    def finalize(self, session: dict) -> str:
        manifest_path = Path(session["session_dir"]) / "manifest.json"
        manifest_path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
        index = self._load_index()
        index.insert(0, {
            "created_at": session["created_at"],
            "stamp": session["stamp"],
            "entry_count": len(session["entries"]),
            "manifest_path": str(manifest_path),
        })
        self._save_index(index[:10])
        return str(manifest_path)

    def list_recent_sessions(self, limit: int = 3) -> list[dict]:
        return self._load_index()[:limit]

    def undo_session(self, manifest_path: str) -> tuple[int, int, list[str]]:
        path = Path(manifest_path)
        if not path.exists():
            return 0, 1, ["指定されたバックアップ情報が見つかりません。"]
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            return 0, 1, [f"バックアップ情報を読めませんでした: {e}"]

        success = 0
        failed = 0
        messages: list[str] = []

        for entry in reversed(manifest.get("entries", [])):
            try:
                op = entry.get("operation")
                target_path = Path(entry.get("target_path", ""))
                backup_path = Path(entry.get("backup_path", ""))
                if not backup_path.exists():
                    failed += 1
                    messages.append(f"戻せませんでした: {target_path}（バックアップなし）")
                    continue

                if op == "trash":
                    if target_path.exists():
                        failed += 1
                        messages.append(f"戻せませんでした: {target_path}（既に同名ファイルあり）")
                        continue
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(backup_path), str(target_path))
                    success += 1
                    messages.append(f"戻しました: {target_path}")
                elif op == "update":
                    source_original_path = Path(entry.get("source_original_path", ""))
                    current_target_file = target_path

                    # いま更新先にある「移動後ファイル」を元の場所へ戻す
                    if current_target_file.exists() and str(source_original_path):
                        if source_original_path.exists():
                            failed += 1
                            messages.append(f"戻せませんでした: {source_original_path}（元の場所に既に同名ファイルあり）")
                            continue
                        source_original_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(current_target_file), str(source_original_path))
                    elif current_target_file.exists():
                        try:
                            current_target_file.unlink()
                        except Exception as e:
                            failed += 1
                            messages.append(f"戻せませんでした: {target_path}（現在ファイル削除失敗: {e}）")
                            continue

                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(backup_path), str(target_path))
                    success += 1
                    messages.append(f"移動更新前の状態に戻しました: {target_path}")
            except Exception as e:
                failed += 1
                messages.append(f"戻せませんでした: {entry.get('target_path', '')} ({e})")

        return success, failed, messages
