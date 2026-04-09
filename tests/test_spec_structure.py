from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


REQUIRED_PATHS = [
    PROJECT_ROOT / "main.py",
    PROJECT_ROOT / "requirements.txt",
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / ".gitignore",
    PROJECT_ROOT / "config",
    PROJECT_ROOT / "config" / "app_config.py",
    PROJECT_ROOT / "config" / "logging_config.py",
    PROJECT_ROOT / "core" / "logic" / "file_management_logic.py",
    PROJECT_ROOT / "core" / "services" / "file_scanner_service.py",
    PROJECT_ROOT / "core" / "services" / "file_operation_service.py",
    PROJECT_ROOT / "core" / "services" / "backup_service.py",
    PROJECT_ROOT / "core" / "utils" / "logger.py",
    PROJECT_ROOT / "core" / "utils" / "path_validator.py",
    PROJECT_ROOT / "ui" / "components",
    PROJECT_ROOT / "tests",
    PROJECT_ROOT / "docs",
    PROJECT_ROOT / "logs",
    PROJECT_ROOT / "data",
]


def test_required_paths_exist() -> None:
    missing = [str(path) for path in REQUIRED_PATHS if not path.exists()]
    assert not missing, f"不足パスがあります: {missing}"
