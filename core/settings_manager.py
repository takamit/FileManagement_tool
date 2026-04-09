from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_SETTINGS: dict[str, Any] = {
    "version": 2,
    "history_limit": 50,
    "default_update_mode": "copy",
    "report_format": "json",
    "report_output_dir": "reports",
    "safety": {
        "require_backup_before_replace": True,
        "allow_move_update": True,
    },
}


class SettingsManager:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.config_dir = self.base_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.config_dir / "settings.json"

    def load(self) -> dict:
        if not self.path.exists():
            return self._clone_defaults()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self._backup_corrupt_file()
            return self._clone_defaults()
        validated = self._validate(raw)
        if validated != raw:
            self.save(validated)
        return validated

    def save(self, data: dict) -> None:
        validated = self._validate(data)
        self.path.write_text(json.dumps(validated, ensure_ascii=False, indent=2), encoding="utf-8")

    def _clone_defaults(self) -> dict:
        return json.loads(json.dumps(DEFAULT_SETTINGS, ensure_ascii=False))

    def _backup_corrupt_file(self) -> None:
        if not self.path.exists():
            return
        corrupt_path = self.path.with_suffix(".corrupt.json")
        suffix = 1
        while corrupt_path.exists():
            corrupt_path = self.path.with_name(f"settings.corrupt.{suffix}.json")
            suffix += 1
        self.path.replace(corrupt_path)

    def _validate(self, data: dict[str, Any] | Any) -> dict:
        merged = self._clone_defaults()
        if not isinstance(data, dict):
            return merged

        version = data.get("version", DEFAULT_SETTINGS["version"])
        if not isinstance(version, int) or version < 1:
            version = DEFAULT_SETTINGS["version"]
        merged["version"] = DEFAULT_SETTINGS["version"]

        history_limit = data.get("history_limit", DEFAULT_SETTINGS["history_limit"])
        if not isinstance(history_limit, int):
            history_limit = DEFAULT_SETTINGS["history_limit"]
        merged["history_limit"] = max(1, min(history_limit, 500))

        update_mode = data.get("default_update_mode", DEFAULT_SETTINGS["default_update_mode"])
        if update_mode not in {"copy", "move"}:
            update_mode = DEFAULT_SETTINGS["default_update_mode"]
        merged["default_update_mode"] = update_mode

        report_format = data.get("report_format", DEFAULT_SETTINGS["report_format"])
        if report_format not in {"json", "csv", "html"}:
            report_format = DEFAULT_SETTINGS["report_format"]
        merged["report_format"] = report_format

        report_output_dir = data.get("report_output_dir", DEFAULT_SETTINGS["report_output_dir"])
        if not isinstance(report_output_dir, str) or not report_output_dir.strip():
            report_output_dir = DEFAULT_SETTINGS["report_output_dir"]
        merged["report_output_dir"] = report_output_dir.strip()

        safety = data.get("safety", {})
        if not isinstance(safety, dict):
            safety = {}
        merged["safety"] = {
            "require_backup_before_replace": bool(
                safety.get(
                    "require_backup_before_replace",
                    DEFAULT_SETTINGS["safety"]["require_backup_before_replace"],
                )
            ),
            "allow_move_update": bool(
                safety.get("allow_move_update", DEFAULT_SETTINGS["safety"]["allow_move_update"])
            ),
        }

        _ = version  # 将来の移行処理用に読み込みだけは行う
        return merged
