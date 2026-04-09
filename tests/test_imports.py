from __future__ import annotations


def test_import_main_modules():
    import main  # noqa: F401
    from ui.gui import FileManagerApp  # noqa: F401
    from core.logic.file_manager_logic import scan_folders  # noqa: F401
