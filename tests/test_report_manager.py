from __future__ import annotations

from pathlib import Path

from core.report_manager import ReportManager


def test_save_report_creates_bundle(tmp_path: Path) -> None:
    manager = ReportManager(str(tmp_path))
    txt_path = manager.save_report({"total": 2}, [{"status": "成功", "target": "a.txt"}])
    assert txt_path.endswith(".txt")
    bundle = manager.last_saved_bundle
    assert set(bundle.keys()) == {"txt", "json", "csv", "html"}
    for path in bundle.values():
        assert Path(path).exists()
