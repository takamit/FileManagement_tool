from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    """アプリケーション全体で利用する基本設定。"""

    app_name: str = "ファイル管理ツール"
    default_mode: str = "gui"
    settings_file: str = "config/settings.json"
    classify_rules_file: str = "config/classify_rules.json"
    log_dir: str = "logs"
    data_dir: str = "data"
    temp_dir: str = "data/temp"
    report_dir: str = "reports"
    backup_dir: str = "backup"
    history_dir: str = "history"
    supported_modes: tuple[str, ...] = ("gui", "cli")
    max_preview_chars: int = 2000
    default_exclude_dirs: list[str] = field(default_factory=list)
    default_exclude_exts: list[str] = field(default_factory=list)

    def resolve(self, project_root: Path) -> dict[str, Path | str | int | tuple[str, ...] | list[str]]:
        return {
            "app_name": self.app_name,
            "default_mode": self.default_mode,
            "settings_file": project_root / self.settings_file,
            "classify_rules_file": project_root / self.classify_rules_file,
            "log_dir": project_root / self.log_dir,
            "data_dir": project_root / self.data_dir,
            "temp_dir": project_root / self.temp_dir,
            "report_dir": project_root / self.report_dir,
            "backup_dir": project_root / self.backup_dir,
            "history_dir": project_root / self.history_dir,
            "supported_modes": self.supported_modes,
            "max_preview_chars": self.max_preview_chars,
            "default_exclude_dirs": list(self.default_exclude_dirs),
            "default_exclude_exts": list(self.default_exclude_exts),
        }
