from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_SETTINGS = {
    "last_target_dir": "",
    "exclude_dirs": [".git", "venv", "__pycache__"],
    "archive_dir_name": "_archive",
    "duplicate_dir_name": "_duplicates",
    "dry_run": True,
    "auto_backup": True,
}

DEFAULT_CLASSIFY_RULES = {
    "Documents/MeetingNotes": ["議事録", "meeting", "minutes"],
    "Documents/Specs": ["設計", "spec", "requirements"],
    "Documents/Contracts": ["契約", "agreement"],
    "Documents/Invoices": ["請求", "invoice"],
    "Code/Python": [".py"],
    "Media/Images": [".png", ".jpg", ".jpeg", ".webp"],
}


class ConfigManager:
    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.config_dir / "settings.json"
        self.rules_path = self.config_dir / "classify_rules.json"
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        if not self.settings_path.exists():
            self.settings_path.write_text(
                json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if not self.rules_path.exists():
            self.rules_path.write_text(
                json.dumps(DEFAULT_CLASSIFY_RULES, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def load_settings(self) -> dict[str, Any]:
        return json.loads(self.settings_path.read_text(encoding="utf-8"))

    def save_settings(self, settings: dict[str, Any]) -> None:
        self.settings_path.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_rules(self) -> dict[str, list[str]]:
        return json.loads(self.rules_path.read_text(encoding="utf-8"))
