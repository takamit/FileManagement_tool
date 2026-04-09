from __future__ import annotations

import json
import shutil
from pathlib import Path


class HistoryManager:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.history_dir = self.base_dir / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.last_run_path = self.history_dir / "last_run.json"

    def save_run(self, results: list[dict]) -> None:
        payload = {
            "results": results,
        }
        with self.last_run_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def load_last_run(self) -> dict | None:
        if not self.last_run_path.exists():
            return None
        try:
            with self.last_run_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def undo_last_run(self) -> tuple[int, int, list[str]]:
        payload = self.load_last_run()
        if not payload:
            return 0, 0, ["取り消し履歴が見つかりません。"]

        success = 0
        failed = 0
        messages: list[str] = []

        for item in reversed(payload.get("results", [])):
            if item.get("status") != "成功":
                continue

            operation = item.get("operation", "archive_only")
            archived_to = item.get("archived_to")
            target = item.get("target")

            try:
                if not archived_to or not target:
                    continue

                archived = Path(archived_to)
                target_path = Path(target)

                if operation == "archive_only":
                    if not archived.exists():
                        failed += 1
                        messages.append(f"戻せませんでした: {archived_to}（退避ファイルが見つかりません）")
                        continue
                    if target_path.exists():
                        failed += 1
                        messages.append(f"戻せませんでした: {target}（元の場所に別ファイルがあります）")
                        continue
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(archived), str(target_path))
                    success += 1
                    messages.append(f"戻しました: {target}")
                    continue

                if operation == "replace_target":
                    if not archived.exists():
                        failed += 1
                        messages.append(f"戻せませんでした: {archived_to}（退避ファイルが見つかりません）")
                        continue

                    if target_path.exists():
                        try:
                            target_path.unlink()
                        except Exception as e:
                            failed += 1
                            messages.append(f"戻せませんでした: {target}（現在の更新版を削除できません: {e}）")
                            continue

                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(archived), str(target_path))
                    success += 1
                    messages.append(f"元に戻しました: {target}")
                    continue

            except Exception as e:
                failed += 1
                messages.append(f"戻せませんでした: {target} ({e})")

        return success, failed, messages
