from __future__ import annotations

from core.logic.cli_controller import CliController, CliScanRequest


def test_cli_controller_scan_returns_summary(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.txt").write_text("hello", encoding="utf-8")

    controller = CliController()
    items, summary = controller.scan(CliScanRequest(source_dir=str(source)))

    assert isinstance(items, list)
    assert isinstance(summary, dict)
