from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
import csv
import html
import json
import shutil

from send2trash import send2trash

from .backup_manager import BackupManager
from .utils.runtime_control import OperationController


@dataclass(slots=True)
class ExecutionPlanEntry:
    operation: str
    action_label: str
    source_path: str
    target_path: str
    item_name: str
    backup_required: bool
    source_selected_side: str


def _selected_path_and_side(item) -> tuple[str, str]:
    if getattr(item, "target_selected", False) and getattr(item, "compare_selected", False):
        raise ValueError("対象フォルダ側と比較フォルダ側の両方が選択されています。")
    if not getattr(item, "target_selected", False) and not getattr(item, "compare_selected", False):
        raise ValueError("対象フォルダ側または比較フォルダ側のどちらかを選択してください。")
    if getattr(item, "target_selected", False):
        return getattr(item, "target_path", ""), "target"
    return getattr(item, "compare_path", ""), "compare"


def build_plan_entry(item) -> ExecutionPlanEntry:
    selected_path, selected_side = _selected_path_and_side(item)
    target_path = getattr(item, "target_path", "")
    compare_path = getattr(item, "compare_path", "")
    preferred_action = getattr(item, "preferred_action", "")

    if preferred_action == "何もしない":
        return ExecutionPlanEntry(
            operation="noop",
            action_label=preferred_action,
            source_path="",
            target_path="",
            item_name=Path(target_path or compare_path).name,
            backup_required=False,
            source_selected_side=selected_side,
        )

    if preferred_action == "選択側のファイルをゴミ箱へ移動":
        return ExecutionPlanEntry(
            operation="trash_selected",
            action_label=preferred_action,
            source_path="",
            target_path=selected_path,
            item_name=Path(selected_path).name,
            backup_required=True,
            source_selected_side=selected_side,
        )

    copy_labels = {
        "選択側のファイルで更新",
        "選択側のファイルで更新（コピー）",
        "選択側のファイルで更新（バックアップ付きコピー）",
    }
    move_labels = {"選択側のファイルで更新（移動）"}

    if preferred_action in copy_labels | move_labels:
        if selected_side == "target":
            source_path = target_path
            destination_path = compare_path
        else:
            source_path = compare_path
            destination_path = target_path
        if preferred_action in move_labels:
            operation = "replace_by_move"
        else:
            operation = "replace_by_copy"
        return ExecutionPlanEntry(
            operation=operation,
            action_label=preferred_action,
            source_path=source_path,
            target_path=destination_path,
            item_name=Path(destination_path).name,
            backup_required=True,
            source_selected_side=selected_side,
        )

    raise ValueError(f"未対応の処理です: {preferred_action}")


def resolve_action(item) -> tuple[str, str]:
    plan = build_plan_entry(item)
    return plan.operation, plan.target_path


def _trash_with_backup(file_path: str, backup_manager: BackupManager, session: dict) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"移動対象が見つかりません: {file_path}")
    backup_path = backup_manager.backup_file(session, file_path)
    send2trash(str(path))
    backup_manager.add_entry(
        session,
        {
            "operation": "trash",
            "target_path": file_path,
            "backup_path": backup_path,
        },
    )
    return backup_path


def _copy_replace_with_backup(source_path: str, target_path: str, backup_manager: BackupManager, session: dict) -> str:
    source = Path(source_path)
    target = Path(target_path)
    if not source.exists():
        raise FileNotFoundError(f"更新元が見つかりません: {source_path}")
    if not target.exists():
        raise FileNotFoundError(f"更新先が見つかりません: {target_path}")

    backup_path = backup_manager.backup_file(session, target_path)
    try:
        shutil.copy2(str(source), str(target))
    except Exception as exc:
        raise RuntimeError(f"ファイルコピーによる更新に失敗しました: {exc}") from exc

    backup_manager.add_entry(
        session,
        {
            "operation": "update_copy",
            "target_path": target_path,
            "backup_path": backup_path,
            "source_original_path": source_path,
        },
    )
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
    except Exception as exc:
        raise RuntimeError(f"更新先ファイルを置き換えられませんでした: {exc}") from exc

    try:
        shutil.move(str(source), str(target))
    except Exception as exc:
        raise RuntimeError(f"ファイル移動による更新に失敗しました: {exc}") from exc

    backup_manager.add_entry(
        session,
        {
            "operation": "update_move",
            "target_path": target_path,
            "backup_path": backup_path,
            "source_original_path": source_path,
        },
    )
    return backup_path


def preview_items(items: Iterable) -> list[dict]:
    rows: list[dict] = []
    for item in items:
        plan = build_plan_entry(item)
        rows.append(
            {
                "name": plan.item_name,
                "operation": plan.operation,
                "action": plan.action_label,
                "source_path": plan.source_path,
                "target_path": plan.target_path,
                "backup_required": plan.backup_required,
                "selected_side": plan.source_selected_side,
            }
        )
    return rows


def export_preview_report(items: Iterable, output_path: str, format_hint: str | None = None) -> str:
    rows = preview_items(items)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    output_format = (format_hint or path.suffix.lstrip(".") or "json").lower()

    if output_format == "json":
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)

    if output_format == "csv":
        fieldnames = [
            "name",
            "operation",
            "action",
            "source_path",
            "target_path",
            "backup_required",
            "selected_side",
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return str(path)

    if output_format == "html":
        header = "".join(f"<th>{html.escape(col)}</th>" for col in rows[0].keys()) if rows else ""
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row.values()) + "</tr>"
            for row in rows
        )
        html_text = f"""<!doctype html>
<html lang=\"ja\">
<head>
  <meta charset=\"utf-8\">
  <title>FileManagement Tool Preview Report</title>
  <style>
    body {{ font-family: sans-serif; margin: 24px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    th {{ background: #f4f4f4; }}
  </style>
</head>
<body>
  <h1>変更予定レポート</h1>
  <p>件数: {len(rows)}</p>
  <table>
    <thead><tr>{header}</tr></thead>
    <tbody>{body}</tbody>
  </table>
</body>
</html>
"""
        path.write_text(html_text, encoding="utf-8")
        return str(path)

    raise ValueError(f"未対応のレポート形式です: {output_format}")


def execute_items(
    items: Iterable,
    backup_manager: BackupManager,
    controller: OperationController,
    progress_cb: Callable[[int, int, str], None] | None = None,
    dry_run: bool = False,
) -> tuple[list[dict], str]:
    items = list(items)
    total = len(items)
    results: list[dict] = []
    session = backup_manager.start_session(metadata={"dry_run": dry_run})

    for idx, item in enumerate(items, start=1):
        controller.check()
        item_name = Path(getattr(item, "target_path", "") or getattr(item, "compare_path", "")).name
        if progress_cb and (idx == 1 or idx == total or idx % 20 == 0):
            progress_cb(idx, total, f"実行中: {item_name}")

        try:
            plan = build_plan_entry(item)
            if dry_run:
                results.append(
                    {
                        "status": "確認のみ",
                        "kind": plan.operation,
                        "target": plan.target_path,
                        "action": plan.action_label,
                        "source_used": plan.source_path,
                        "message": "dry-run のため、実ファイルは変更していません。",
                    }
                )
                continue

            if plan.operation == "noop":
                results.append(
                    {
                        "status": "成功",
                        "kind": "スキップ",
                        "target": "",
                        "action": plan.action_label,
                        "message": "処理なし",
                    }
                )
            elif plan.operation == "trash_selected":
                backup = _trash_with_backup(plan.target_path, backup_manager, session)
                results.append(
                    {
                        "status": "成功",
                        "kind": "削除",
                        "target": plan.target_path,
                        "action": plan.action_label,
                        "backup_path": backup,
                        "message": "選択側ファイルをゴミ箱へ移動しました。",
                    }
                )
            elif plan.operation == "replace_by_copy":
                backup = _copy_replace_with_backup(plan.source_path, plan.target_path, backup_manager, session)
                results.append(
                    {
                        "status": "成功",
                        "kind": "更新",
                        "target": plan.target_path,
                        "action": plan.action_label,
                        "source_used": plan.source_path,
                        "backup_path": backup,
                        "message": "選択側ファイルをコピーして更新しました。更新元は保持されます。",
                    }
                )
            elif plan.operation == "replace_by_move":
                backup = _move_replace_with_backup(plan.source_path, plan.target_path, backup_manager, session)
                results.append(
                    {
                        "status": "成功",
                        "kind": "更新",
                        "target": plan.target_path,
                        "action": plan.action_label,
                        "source_used": plan.source_path,
                        "backup_path": backup,
                        "message": "選択側ファイルを移動して更新しました。更新元は元の場所から消えます。",
                    }
                )
            else:
                raise ValueError(f"未対応の内部処理です: {plan.operation}")
        except InterruptedError:
            results.append(
                {
                    "status": "停止",
                    "kind": "停止",
                    "target": getattr(item, "target_path", ""),
                    "action": getattr(item, "preferred_action", ""),
                    "error": "処理は停止されました。",
                }
            )
            break
        except Exception as exc:
            results.append(
                {
                    "status": "失敗",
                    "kind": "エラー",
                    "target": getattr(item, "target_path", ""),
                    "action": getattr(item, "preferred_action", ""),
                    "error": str(exc),
                }
            )

    manifest_path = backup_manager.finalize(session)
    return results, manifest_path
