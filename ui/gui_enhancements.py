from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from core.backup_manager import BackupManager
from core.executor import export_preview_report, preview_items


SAFE_COPY_LABEL = "選択側のファイルで更新（安全コピー）"
MOVE_LABEL = "選択側のファイルで更新（移動）"


def display_action_label(label: str) -> str:
    if label == "選択側のファイルで更新":
        return SAFE_COPY_LABEL
    return label


class HistoryDialog(tk.Toplevel):
    def __init__(self, master, sessions: list[dict], backup_manager: BackupManager, report_manager) -> None:
        super().__init__(master)
        self.title("バックアップ履歴")
        self.geometry("1100x620")
        self.transient(master)
        self.grab_set()
        self._sessions = sessions
        self._backup_manager = backup_manager
        self._report_manager = report_manager

        wrap = ttk.Frame(self, padding=12)
        wrap.pack(fill="both", expand=True)

        ttk.Label(wrap, text="バックアップ履歴一覧", font=("Yu Gothic UI", 13, "bold")).pack(anchor="w")
        ttk.Label(
            wrap,
            text="件数、操作種別、dry-run などを確認した上で、必要な履歴だけ元に戻せます。",
        ).pack(anchor="w", pady=(4, 8))

        cols = ("created_at", "entry_count", "operations", "dry_run", "manifest_path")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", height=12)
        labels = {
            "created_at": "作成日時",
            "entry_count": "件数",
            "operations": "操作内訳",
            "dry_run": "dry-run",
            "manifest_path": "manifest",
        }
        widths = {"created_at": 160, "entry_count": 80, "operations": 260, "dry_run": 80, "manifest_path": 420}
        for col in cols:
            self.tree.heading(col, text=labels[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.pack(fill="x", expand=False)
        self.tree.bind("<<TreeviewSelect>>", self._show_details)

        detail_wrap = ttk.LabelFrame(wrap, text="詳細")
        detail_wrap.pack(fill="both", expand=True, pady=(10, 8))
        self.detail = tk.Text(detail_wrap, wrap="word", height=16)
        self.detail.pack(fill="both", expand=True)

        btn = ttk.Frame(wrap)
        btn.pack(fill="x")
        ttk.Button(btn, text="履歴レポートを出力", command=self._export_selected).pack(side="left")
        ttk.Button(btn, text="選択した履歴を元に戻す", command=self._undo_selected).pack(side="right")
        ttk.Button(btn, text="閉じる", command=self.destroy).pack(side="right", padx=8)

        for i, session in enumerate(sessions):
            operations = session.get("operations", {})
            operations_text = ", ".join(f"{k}:{v}" for k, v in operations.items()) or "-"
            metadata = session.get("metadata", {})
            dry_run = "はい" if metadata.get("dry_run") else "いいえ"
            self.tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    session.get("created_at", ""),
                    session.get("entry_count", 0),
                    operations_text,
                    dry_run,
                    session.get("manifest_path", ""),
                ),
            )
        if sessions:
            self.tree.selection_set("0")
            self._show_details()

    def _selected_manifest(self) -> str | None:
        selection = self.tree.selection()
        if not selection:
            return None
        idx = int(selection[0])
        return self._sessions[idx].get("manifest_path")

    def _show_details(self, _event=None) -> None:
        manifest_path = self._selected_manifest()
        if not manifest_path:
            return
        details = self._backup_manager.describe_session(manifest_path)
        lines = [
            f"stamp: {details.get('stamp', '')}",
            f"created_at: {details.get('created_at', '')}",
            f"entry_count: {details.get('entry_count', 0)}",
            f"operations: {details.get('operations', {})}",
            f"metadata: {details.get('metadata', {})}",
            "",
            "entries:",
        ]
        for entry in details.get("entries", []):
            lines.append(
                f"[{entry.get('no')}] {entry.get('operation')} / target={entry.get('target_path', '')} / source={entry.get('source_original_path', '')}"
            )
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", "\n".join(lines))

    def _export_selected(self) -> None:
        manifest_path = self._selected_manifest()
        if not manifest_path:
            return
        details = self._backup_manager.describe_session(manifest_path)
        bundle = self._report_manager.save_history_report(details)
        messagebox.showinfo("履歴レポート", "履歴レポートを出力しました。\n\n" + "\n".join(bundle.values()), parent=self)

    def _undo_selected(self) -> None:
        manifest_path = self._selected_manifest()
        if not manifest_path:
            return
        if not messagebox.askyesno("確認", "この履歴を元に戻します。よろしいですか？", parent=self):
            return
        success, failed, messages = self._backup_manager.undo_session(manifest_path)
        messagebox.showinfo(
            "元に戻す",
            f"成功: {success}件 / 失敗: {failed}件\n\n" + "\n".join(messages[:20]),
            parent=self,
        )
        self.destroy()


def apply_gui_enhancements(file_manager_app_cls) -> None:
    if getattr(file_manager_app_cls, "_v98_enhanced", False):
        return
    file_manager_app_cls._v98_enhanced = True

    original_init = file_manager_app_cls.__init__
    original_execute = getattr(file_manager_app_cls, "execute", None)
    original_show_detail = getattr(file_manager_app_cls, "show_detail", None)
    original_row_values = getattr(file_manager_app_cls, "_row_values", None)

    def _walk_widgets(widget):
        yield widget
        for child in widget.winfo_children():
            yield from _walk_widgets(child)

    def _replace_static_texts(app) -> None:
        for widget in _walk_widgets(app.root):
            try:
                text = widget.cget("text")
            except Exception:
                continue
            if not isinstance(text, str):
                continue
            if "更新はコピーではなく移動更新です" in text:
                widget.configure(text="※ 通常の『更新』は安全コピーです。元ファイルは残ります。移動を使うときだけ元ファイルが消えます。")
            elif text == "直近3件から元に戻す":
                widget.configure(text="履歴一覧から元に戻す")

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.last_execution_bundle = {}
        self.last_preview_bundle = {}
        _replace_static_texts(self)
        _install_extension_menu(self)
        _install_notice_banner(self)

    def _install_extension_menu(app) -> None:
        try:
            menubar = app.root.nametowidget(app.root["menu"])
        except Exception:
            return
        ext_menu = tk.Menu(menubar, tearoff=False)
        ext_menu.add_command(label="変更予定レポートを出力", command=lambda: export_current_preview_bundle(app))
        ext_menu.add_command(label="実行結果レポート保存先を開く", command=lambda: show_last_execution_bundle(app))
        ext_menu.add_separator()
        ext_menu.add_command(label="履歴一覧を開く", command=lambda: open_history_dialog(app))
        menubar.add_cascade(label="拡張", menu=ext_menu)

    def _install_notice_banner(app) -> None:
        try:
            banner = ttk.Frame(app.outer, padding=(12, 8))
            first_child = app.outer.winfo_children()[0] if app.outer.winfo_children() else None
            banner.pack(fill="x", pady=(0, 10), before=first_child)
            ttk.Label(
                banner,
                text="既定の更新は『安全コピー』です。元ファイルは残ります。移動更新だけが元ファイルを移動します。",
                foreground="#2b5d34",
            ).pack(anchor="w")
        except Exception:
            pass

    def export_current_preview_bundle(app) -> None:
        if not getattr(app, "scan_items", None):
            messagebox.showinfo("変更予定レポート", "まだスキャン結果がありません。")
            return
        selected = [item for item in app.scan_items if getattr(item, "target_selected", False) or getattr(item, "compare_selected", False)]
        rows = preview_items(selected or app.scan_items)
        for row in rows:
            row["action"] = display_action_label(str(row.get("action", "")))
        bundle = app.report_manager.save_preview_report(getattr(app, "last_scan_summary", {}), rows)
        app.last_preview_bundle = bundle
        messagebox.showinfo("変更予定レポート", "変更予定レポートを出力しました。\n\n" + "\n".join(bundle.values()))

    def show_last_execution_bundle(app) -> None:
        if not getattr(app, "last_execution_bundle", None):
            report_dir = Path(app.base_dir) / "reports"
            messagebox.showinfo("実行結果レポート", f"最新レポートは reports フォルダを確認してください。\n{report_dir}")
            return
        messagebox.showinfo("実行結果レポート", "最新の実行結果レポート\n\n" + "\n".join(app.last_execution_bundle.values()))

    def open_history_dialog(app) -> None:
        history_limit = int(app.settings.get("history_limit", 50)) if isinstance(getattr(app, "settings", None), dict) else 50
        manager = BackupManager(app.base_dir, max_sessions=history_limit)
        sessions = manager.list_recent_sessions(limit=None)
        if not sessions:
            messagebox.showinfo("バックアップ履歴", "表示できる履歴がありません。")
            return
        HistoryDialog(app.root, sessions, manager, app.report_manager)

    def execute(self, *args, **kwargs):
        before = set(Path(self.base_dir).joinpath("reports").glob("*"))
        result = original_execute(self, *args, **kwargs) if callable(original_execute) else None
        report_dir = Path(self.base_dir) / "reports"
        after = sorted(set(report_dir.glob("*")) - before, key=lambda p: p.stat().st_mtime)
        if after:
            grouped: dict[str, str] = {}
            for path in after:
                grouped[path.suffix.lstrip(".") or path.name] = str(path)
            self.last_execution_bundle = grouped
        return result

    def show_detail(self, indices):
        result = original_show_detail(self, indices)
        text_widget = getattr(self, "detail_info", None)
        if text_widget is not None:
            try:
                content = text_widget.get("1.0", "end")
                content = content.replace("現在の処理: 選択側のファイルで更新\n", f"現在の処理: {SAFE_COPY_LABEL}\n")
                text_widget.delete("1.0", "end")
                text_widget.insert("1.0", content)
            except Exception:
                pass
        return result

    def _row_values(self, row):
        values = original_row_values(self, row) if callable(original_row_values) else {}
        if "action" in values:
            values["action"] = display_action_label(str(values["action"]))
        return values

    def undo_recent(self):
        open_history_dialog(self)

    file_manager_app_cls.__init__ = __init__
    if callable(original_execute):
        file_manager_app_cls.execute = execute
    if callable(original_show_detail):
        file_manager_app_cls.show_detail = show_detail
    if callable(original_row_values):
        file_manager_app_cls._row_values = _row_values
    file_manager_app_cls.undo_recent = undo_recent

    try:
        import ui.gui as gui_mod
    except Exception:
        gui_mod = None
    if gui_mod is not None and hasattr(gui_mod, "ConfirmationDialog"):
        dialog_cls = gui_mod.ConfirmationDialog
        original_refresh = getattr(dialog_cls, "refresh", None)
        if callable(original_refresh):
            def refresh(self, items):
                original_refresh(self, items)
                for iid in self.tree.get_children():
                    values = list(self.tree.item(iid, "values"))
                    if len(values) >= 2:
                        values[1] = display_action_label(str(values[1]))
                        self.tree.item(iid, values=values)
            dialog_cls.refresh = refresh
