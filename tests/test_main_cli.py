from __future__ import annotations

import json
from pathlib import Path
import types

import main


class DummyController:
    def scan(self, request):
        return [object(), object()], {"dummy": 2}

    def preview(self, request):
        return [{"operation": "replace_by_copy"}]

    def export_preview(self, request, output_path: str, format_hint: str | None = None):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("[]", encoding="utf-8")
        return output_path

    def apply(self, request, base_dir: str, dry_run: bool = False):
        return [{"status": "確認のみ" if dry_run else "成功"}], str(Path(base_dir) / "backup" / "manifest.json")


class DummyBackupManager:
    def __init__(self, *args, **kwargs):
        pass

    def list_recent_sessions(self, limit: int = 1):
        return [{"manifest_path": "dummy.json"}]

    def undo_session(self, manifest_path: str):
        return 1, 0, [f"undone: {manifest_path}"]


def test_run_cli_preview(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(main, "CliController", DummyController)
    args = types.SimpleNamespace(
        source="/tmp/source",
        compare="/tmp/compare",
        exclude_dirs="",
        exclude_exts="",
        action="preview",
        dry_run=False,
        report="",
        report_format="",
        base_dir=str(tmp_path),
        undo_manifest="",
    )
    rc = main.run_cli(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["items"][0]["operation"] == "replace_by_copy"


def test_run_cli_undo_last(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(main, "BackupManager", DummyBackupManager)
    args = types.SimpleNamespace(
        source="",
        compare="",
        exclude_dirs="",
        exclude_exts="",
        action="undo-last",
        dry_run=False,
        report="",
        report_format="",
        base_dir=str(tmp_path),
        undo_manifest="",
    )
    rc = main.run_cli(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] == 1
