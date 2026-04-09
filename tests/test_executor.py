from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.backup_manager import BackupManager
from core.executor import build_plan_entry, execute_items
from core.utils.runtime_control import OperationController


@dataclass
class DummyItem:
    target_path: str
    compare_path: str
    target_selected: bool
    compare_selected: bool
    preferred_action: str


def test_default_update_is_safe_copy(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    compare = tmp_path / "compare.txt"
    source.write_text("new", encoding="utf-8")
    compare.write_text("old", encoding="utf-8")
    item = DummyItem(str(source), str(compare), True, False, "選択側のファイルで更新")

    plan = build_plan_entry(item)
    assert plan.operation == "replace_by_copy"

    results, _ = execute_items([item], BackupManager(str(tmp_path)), OperationController())

    assert results[0]["status"] == "成功"
    assert source.read_text(encoding="utf-8") == "new"
    assert compare.read_text(encoding="utf-8") == "new"


def test_move_update_still_supported(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    compare = tmp_path / "compare.txt"
    source.write_text("new", encoding="utf-8")
    compare.write_text("old", encoding="utf-8")
    item = DummyItem(str(source), str(compare), True, False, "選択側のファイルで更新（移動）")

    results, _ = execute_items([item], BackupManager(str(tmp_path)), OperationController())

    assert results[0]["status"] == "成功"
    assert not source.exists()
    assert compare.read_text(encoding="utf-8") == "new"


def test_dry_run_does_not_touch_files(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    compare = tmp_path / "compare.txt"
    source.write_text("new", encoding="utf-8")
    compare.write_text("old", encoding="utf-8")
    item = DummyItem(str(source), str(compare), True, False, "選択側のファイルで更新")

    results, _ = execute_items([item], BackupManager(str(tmp_path)), OperationController(), dry_run=True)

    assert results[0]["status"] == "確認のみ"
    assert source.read_text(encoding="utf-8") == "new"
    assert compare.read_text(encoding="utf-8") == "old"
