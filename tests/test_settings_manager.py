from __future__ import annotations

from pathlib import Path

from core.settings_manager import SettingsManager


def test_load_returns_defaults_when_missing(tmp_path: Path) -> None:
    manager = SettingsManager(str(tmp_path))
    data = manager.load()
    assert data["version"] == 2
    assert data["default_update_mode"] == "copy"
    assert data["history_limit"] == 50


def test_invalid_values_are_normalized(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "settings.json").write_text(
        '{"history_limit": "x", "default_update_mode": "unsafe", "report_format": "xml", "safety": []}',
        encoding="utf-8",
    )
    manager = SettingsManager(str(tmp_path))
    data = manager.load()
    assert data["history_limit"] == 50
    assert data["default_update_mode"] == "copy"
    assert data["report_format"] == "json"
    assert data["safety"]["require_backup_before_replace"] is True
