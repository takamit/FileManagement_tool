from __future__ import annotations

import math
import os
import queue
import threading
import time
import difflib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont
from datetime import datetime

from core.services.backup_manager import BackupManager
from core.services.content_tools import read_text_preview
from core.logic.file_manager_logic import execute_items
from core.utils.log_manager import LogManager
from core.services.report_manager import ReportManager
from core.utils.runtime_control import OperationController
from core.logic.file_manager_logic import ScanItem, scan_folders
from core.services.settings_manager import SettingsManager
from core.utils.formatters import bytes_text


class ConfirmationDialog(tk.Toplevel):
    def __init__(self, master, items: list[ScanItem]):
        super().__init__(master)
        self.title("最終確認")
        self.geometry("1180x700")
        self.result = False
        self.transient(master)
        self.grab_set()

        wrap = ttk.Frame(self, padding=12)
        wrap.pack(fill="both", expand=True)

        ttk.Label(wrap, text="実行前の最終確認", font=("Yu Gothic UI", 14, "bold")).pack(anchor="w")

        counts = {}
        total_target = 0
        total_compare = 0
        for item in items:
            side = "対象側" if item.target_selected else "比較側"
            key = f"{side}: {item.preferred_action}"
            counts[key] = counts.get(key, 0) + 1
            total_target += max(0, item.target_size)
            total_compare += max(0, item.compare_size)

        lines = [f"対象件数: {len(items)}件", f"対象側サイズ合計: {bytes_text(total_target)}", f"比較側サイズ合計: {bytes_text(total_compare)}", ""]
        for k, v in counts.items():
            lines.append(f"・{k}: {v}件")
        ttk.Label(wrap, text="\n".join(lines), justify="left").pack(anchor="w", pady=(8, 8))

        top = ttk.Frame(wrap)
        top.pack(fill="x", pady=(0, 6))
        self.filter_var = tk.StringVar(value="すべて")
        ttk.Label(top, text="表示:").pack(side="left")
        cmb = ttk.Combobox(top, textvariable=self.filter_var, state="readonly", width=18, values=["すべて", "削除のみ", "更新のみ"])
        cmb.pack(side="left", padx=6)
        cmb.bind("<<ComboboxSelected>>", lambda e: self.refresh(items))

        table = ttk.Frame(wrap)
        table.pack(fill="both", expand=True)
        cols = ("side", "action", "target_size", "compare_size", "target", "source", "undo")
        self.tree = ttk.Treeview(table, columns=cols, show="headings")
        labels = {
            "side": "選択側",
            "action": "処理",
            "target_size": "対象側サイズ",
            "compare_size": "比較側サイズ",
            "target": "対象",
            "source": "相手側 / 更新元",
            "undo": "元に戻せるか",
        }
        widths = {"side": 90, "action": 180, "target_size": 100, "compare_size": 100, "target": 300, "source": 300, "undo": 100}
        for col in cols:
            self.tree.heading(col, text=labels[col])
            self.tree.column(col, width=widths[col], anchor="w")
        ys = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        xs = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)

        btn = ttk.Frame(wrap)
        btn.pack(fill="x", pady=(8, 0))
        ttk.Button(btn, text="実行する", command=self._ok).pack(side="right")
        ttk.Button(btn, text="戻る", command=self._cancel).pack(side="right", padx=8)

        self.refresh(items)

    def refresh(self, items: list[ScanItem]):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        mode = self.filter_var.get()
        for idx, item in enumerate(items):
            if mode == "削除のみ" and "ゴミ箱" not in item.preferred_action:
                continue
            if mode == "更新のみ" and "更新" not in item.preferred_action:
                continue
            side = "対象側" if item.target_selected else "比較側"
            target = item.target_path if item.target_selected else item.compare_path
            source = item.compare_path if item.target_selected else item.target_path
            self.tree.insert("", "end", iid=str(idx), values=(
                side, item.preferred_action, bytes_text(item.target_size), bytes_text(item.compare_size), target, source, "はい"
            ))

    def _ok(self):
        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()


class UndoSelectDialog(tk.Toplevel):
    def __init__(self, master, sessions: list[dict]):
        super().__init__(master)
        self.title("元に戻すセッションを選択")
        self.geometry("820x380")
        self.result_manifest_path = None
        self.transient(master)
        self.grab_set()

        wrap = ttk.Frame(self, padding=12)
        wrap.pack(fill="both", expand=True)
        ttk.Label(wrap, text="直近のバックアップセッション", font=("Yu Gothic UI", 13, "bold")).pack(anchor="w")

        cols = ("created_at", "entry_count", "manifest_path")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings")
        self.tree.heading("created_at", text="作成日時")
        self.tree.heading("entry_count", text="件数")
        self.tree.heading("manifest_path", text="バックアップ情報")
        self.tree.column("created_at", width=180)
        self.tree.column("entry_count", width=80)
        self.tree.column("manifest_path", width=500)
        self.tree.pack(fill="both", expand=True, pady=(8, 8))

        for i, s in enumerate(sessions):
            self.tree.insert("", "end", iid=str(i), values=(s.get("created_at", ""), s.get("entry_count", 0), s.get("manifest_path", "")))

        btn = ttk.Frame(wrap)
        btn.pack(fill="x")
        ttk.Button(btn, text="選択したセッションを元に戻す", command=lambda: self._ok(sessions)).pack(side="right")
        ttk.Button(btn, text="閉じる", command=self.destroy).pack(side="right", padx=8)

    def _ok(self, sessions):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self.result_manifest_path = sessions[idx].get("manifest_path")
        self.destroy()


class FileManagerApp:
    DEFAULT_COLUMNS = [
        "target_selected", "compare_selected", "category", "confidence",
        "action", "target_size", "compare_size", "reason", "scope", "target", "compare"
    ]
    COLUMN_LABELS = {
        "target_selected": "対象",
        "compare_selected": "比較",
        "category": "種類",
        "confidence": "信頼度",
        "action": "選択中の処理",
        "target_size": "対象側サイズ",
        "compare_size": "比較側サイズ",
        "reason": "理由",
        "scope": "範囲",
        "target": "対象側ファイル",
        "compare": "比較側ファイル",
    }
    COLUMN_MIN_WIDTH = {
        "target_selected": 55,
        "compare_selected": 55,
        "category": 110,
        "confidence": 70,
        "action": 180,
        "target_size": 95,
        "compare_size": 95,
        "reason": 180,
        "scope": 90,
        "target": 260,
        "compare": 260,
    }
    PAGE_SIZE = 1000

    def __init__(self) -> None:
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.settings_manager = SettingsManager(self.base_dir)
        self.report_manager = ReportManager(self.base_dir)
        self.backup_manager = BackupManager(self.base_dir)
        self.log_manager = LogManager()
        self.settings = self.settings_manager.load()

        self.root = tk.Tk()
        self.root.title("ファイル管理ツール")
        self.root.geometry(self.settings.get("window_geometry", "1500x940"))
        self.root.minsize(1280, 860)

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        self._apply_styles()

        self.source_var = tk.StringVar(value=self.settings.get("last_source_dir", ""))
        self.compare_var = tk.StringVar(value=self.settings.get("last_compare_dir", ""))
        self.exclude_dirs_var = tk.StringVar(value=", ".join(self.settings.get("exclude_dirs", [])))
        self.exclude_exts_var = tk.StringVar(value=", ".join(self.settings.get("exclude_exts", [])))
        self.filter_var = tk.StringVar(value=self.settings.get("filter_mode", "すべて"))
        self.search_var = tk.StringVar(value=self.settings.get("search_text", ""))

        self.status_var = tk.StringVar(value="フォルダを選択してスキャンしてください")
        self.progress_label_var = tk.StringVar(value="0%")
        self.eta_var = tk.StringVar(value="残り時間: --:--:--")
        self.summary_var = tk.StringVar(value="対象フォルダ 0件 / 比較フォルダ 0件 / 同一 0件 / 更新候補 0件 / 同名同サイズ 0件 / 同名別内容(対象側大) 0件 / 同名別内容(比較側大) 0件 / 同名別内容(同サイズ) 0件 / サイズ差分 0件")
        self.run_state_var = tk.StringVar(value="待機中")
        self.statusbar_var = tk.StringVar(value="対象側選択 0件 / 比較側選択 0件 / 実行予定 0件 / 最終スキャン --")
        self.action_var = tk.StringVar(value="何もしない")
        self.column_pick_var = tk.StringVar()
        self.page_info_var = tk.StringVar(value="1 / 1")
        self.sort_direction_var = tk.StringVar(value="昇順")
        self.sort_label_var = tk.StringVar(value="並び替えなし")

        saved_order = self.settings.get("column_order", self.DEFAULT_COLUMNS)
        self.column_order = [c for c in saved_order if c in self.DEFAULT_COLUMNS]
        for c in self.DEFAULT_COLUMNS:
            if c not in self.column_order:
                self.column_order.append(c)
        self.column_widths = self.settings.get("column_widths", {})
        self.page = int(self.settings.get("page", 1))

        self.scan_items = []
        self.filtered_indices = []
        self.current_detail_indices = []
        self.last_scan_summary = {}
        self.last_scan_time = "--"
        self.start_time = None
        self.drag_col = None
        self.current_sort_column = self.settings.get("sort_column")
        self.current_sort_reverse = bool(self.settings.get("sort_reverse", False))

        self.scan_queue = queue.Queue()
        self.execute_queue = queue.Queue()
        self.scan_controller = OperationController()
        self.execute_controller = OperationController()
        self.is_scanning = False
        self.is_executing = False

        self._build_scrollable_window()
        self._build_menu()
        self._build_layout()
        if self.current_sort_column in self.COLUMN_LABELS:
            self.sort_direction_var.set("降順" if self.current_sort_reverse else "昇順")
            self.sort_tree_by(self.current_sort_column, self.current_sort_reverse)
        else:
            self.sort_label_var.set("並び替えなし")
        self._settings_snapshot = self._collect_settings_payload()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(80, self._poll_queues)

    # --- build ---
    def _build_scrollable_window(self):
        self.canvas = tk.Canvas(self.root, bg="#f3f6fb", highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self.root, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.outer = ttk.Frame(self.canvas, padding=14)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.outer, anchor="nw")
        self.outer.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=max(e.width, 1200)))
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def _apply_styles(self):
        self.root.configure(bg="#f3f6fb")
        self.style.configure("Title.TLabel", font=("Yu Gothic UI", 18, "bold"), background="#f3f6fb")
        self.style.configure("Sub.TLabel", font=("Yu Gothic UI", 10), background="#f3f6fb", foreground="#506070")
        self.style.configure("Card.TFrame", relief="solid", borderwidth=1, background="#ffffff")
        self.style.configure("Accent.TButton", padding=(14, 8))
        self.style.configure("State.TLabel", font=("Yu Gothic UI", 10, "bold"), background="#f3f6fb")
        self.style.configure("Green.Horizontal.TProgressbar", troughcolor="#dfe6ee", background="#2e8b57", lightcolor="#2e8b57", darkcolor="#2e8b57", bordercolor="#dfe6ee")
        self.style.configure("Treeview", rowheight=30, font=("Yu Gothic UI", 10))
        self.style.configure("Treeview.Heading", font=("Yu Gothic UI", 10, "bold"))

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="対象フォルダを選択", command=self.choose_source)
        file_menu.add_command(label="比較フォルダを選択", command=self.choose_compare)
        file_menu.add_separator()
        file_menu.add_command(label="設定を保存", command=self.save_settings)
        file_menu.add_command(label="終了", command=self.on_close)
        menubar.add_cascade(label="ファイル", menu=file_menu)

        action_menu = tk.Menu(menubar, tearoff=False)
        action_menu.add_command(label="スキャン", command=self.scan)
        action_menu.add_command(label="変更内容を確認", command=self.preview_changes)
        action_menu.add_command(label="実行", command=self.execute)
        action_menu.add_separator()
        action_menu.add_command(label="直近3件から元に戻す", command=self.undo_recent)
        menubar.add_cascade(label="操作", menu=action_menu)

        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_command(label="ログをクリア", command=self.clear_log)
        view_menu.add_command(label="列幅を自動調整", command=self.auto_fit_columns)
        menubar.add_cascade(label="表示", menu=view_menu)

        property_menu = tk.Menu(menubar, tearoff=False)
        property_menu.add_command(label="列順を初期状態に戻す", command=self.reset_columns_to_default)
        property_menu.add_command(label="列幅を自動調整", command=self.auto_fit_columns)
        property_menu.add_separator()
        property_menu.add_command(label="現在の設定を保存", command=self.save_settings)
        menubar.add_cascade(label="プロパティ", menu=property_menu)

        self.root.config(menu=menubar)

    def _build_layout(self):
        header = ttk.Frame(self.outer)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="ファイル管理ツール", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="大規模件数でも扱いやすいよう、バックグラウンド処理・一時停止 / 再開 / 停止・最終確認・バックアップ復元に対応しています。", style="Sub.TLabel").pack(anchor="w", pady=(4, 0))

        paths = ttk.Frame(self.outer, style="Card.TFrame", padding=12)
        paths.pack(fill="x", pady=(0, 10))
        self._path_row(paths, 0, "対象フォルダ", self.source_var, self.choose_source)
        self._path_row(paths, 1, "比較フォルダ（任意）", self.compare_var, self.choose_compare)
        self._entry_row(paths, 2, "除外フォルダ", self.exclude_dirs_var)
        self._entry_row(paths, 3, "除外拡張子", self.exclude_exts_var)

        toolbar = ttk.Frame(self.outer)
        toolbar.pack(fill="x", pady=(0, 8))
        self.scan_btn = ttk.Button(toolbar, text="1. スキャン", command=self.scan, style="Accent.TButton")
        self.scan_btn.pack(side="left")
        self.preview_btn = ttk.Button(toolbar, text="2. 変更内容を確認（0件）", command=self.preview_changes)
        self.preview_btn.pack(side="left", padx=8)
        self.exec_btn = ttk.Button(toolbar, text="3. 実行（0件）", command=self.execute)
        self.exec_btn.pack(side="left")
        ttk.Button(toolbar, text="合計サイズが小さいフォルダ側を全て選択", command=self.select_smaller_side).pack(side="left", padx=(18, 6))
        ttk.Button(toolbar, text="合計サイズが大きいフォルダ側を全て選択", command=self.select_larger_side).pack(side="left", padx=6)

        toolbar2 = ttk.Frame(self.outer)
        toolbar2.pack(fill="x", pady=(0, 10))
        ttk.Button(toolbar2, text="対象フォルダを全て選択", command=self.select_all_target).pack(side="left")
        ttk.Button(toolbar2, text="比較フォルダを全て選択", command=self.select_all_compare).pack(side="left", padx=6)
        ttk.Button(toolbar2, text="対象側選択を全て解除", command=self.clear_target_selection).pack(side="left", padx=6)
        ttk.Button(toolbar2, text="比較側選択を全て解除", command=self.clear_compare_selection).pack(side="left", padx=6)
        ttk.Button(toolbar2, text="全て選択解除", command=self.clear_all_selection).pack(side="left", padx=6)
        self.pause_btn = ttk.Button(toolbar2, text="一時停止", command=self.pause_current, state="disabled")
        self.pause_btn.pack(side="left", padx=(24, 6))
        self.resume_btn = ttk.Button(toolbar2, text="再開", command=self.resume_current, state="disabled")
        self.resume_btn.pack(side="left", padx=6)
        self.stop_btn = ttk.Button(toolbar2, text="停止", command=self.stop_current, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        ttk.Label(toolbar2, textvariable=self.run_state_var, style="State.TLabel").pack(side="left", padx=(18, 0))

        hint = ttk.Frame(self.outer)
        hint.pack(fill="x", pady=(0, 10))
        ttk.Label(hint, text="※ 『合計サイズが小さい / 大きい』は、対象フォルダ全体と比較フォルダ全体の総ファイルサイズを比べて、一括選択する機能です。", style="Sub.TLabel").pack(anchor="w")
        ttk.Label(hint, text="※ 一覧の背景色は種類ごとの区別用です。薄い色で統一し、文字の読みやすさを優先しています。", style="Sub.TLabel").pack(anchor="w", pady=(2, 0))
        ttk.Label(hint, text="※ 更新はコピーではなく移動更新です。更新後、選択側ファイルは元の場所から無くなります。", style="Sub.TLabel").pack(anchor="w", pady=(2, 0))
        ttk.Label(hint, text="※ zip内画像数は中身一覧のみ確認します。zip内zipは再帰せず、読取失敗時は件数に含めません。", style="Sub.TLabel").pack(anchor="w", pady=(2, 0))

        colbar = ttk.Frame(self.outer)
        colbar.pack(fill="x", pady=(0, 10))
        ttk.Label(colbar, text="一覧の並び:").pack(side="left")
        self.column_picker = ttk.Combobox(colbar, textvariable=self.column_pick_var, state="readonly", width=24, values=[self.COLUMN_LABELS[c] for c in self.column_order])
        self.column_picker.pack(side="left", padx=(6, 6))
        ttk.Button(colbar, text="← 左へ", command=self.move_column_left).pack(side="left")
        ttk.Button(colbar, text="右へ →", command=self.move_column_right).pack(side="left", padx=6)

        ttk.Separator(colbar, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Label(colbar, text="一覧のソート:").pack(side="left")
        self.sort_picker = ttk.Combobox(colbar, textvariable=self.column_pick_var, state="readonly", width=24, values=[self.COLUMN_LABELS[c] for c in self.column_order])
        self.sort_picker.pack(side="left", padx=(6, 6))
        self.sort_order_combo = ttk.Combobox(colbar, textvariable=self.sort_direction_var, state="readonly", width=8, values=["昇順", "降順"])
        self.sort_order_combo.pack(side="left", padx=(0, 6))
        ttk.Button(colbar, text="ソートを適用", command=self.apply_sort_from_picker).pack(side="left")
        ttk.Button(colbar, text="ソート解除", command=self.clear_sort).pack(side="left", padx=6)

        ttk.Button(colbar, text="列幅を自動調整", command=self.auto_fit_columns).pack(side="left", padx=12)
        ttk.Label(colbar, textvariable=self.sort_label_var, style="Sub.TLabel").pack(side="left", padx=8)

        colhint = ttk.Frame(self.outer)
        colhint.pack(fill="x", pady=(0, 10))
        ttk.Label(colhint, text="※ 見出しドラッグまたは『← 左へ / 右へ →』で列位置を変更できます。", style="Sub.TLabel").pack(anchor="w")
        ttk.Label(colhint, text="※ 見出しクリックまたは『一覧のソート』で並び替えできます。", style="Sub.TLabel").pack(anchor="w", pady=(2, 0))
        ttk.Label(colhint, text="※ 一覧の 対象 / 比較 欄はクリックで切替できます。", style="Sub.TLabel").pack(anchor="w", pady=(2, 0))

        search = ttk.Frame(self.outer)
        search.pack(fill="x", pady=(0, 10))
        ttk.Label(search, text="表示:").pack(side="left")
        cmb = ttk.Combobox(search, textvariable=self.filter_var, state="readonly", width=20,
                           values=["すべて","同一ファイルのみ","更新候補のみ","同名・同サイズのみ","同名・別内容（対象側が大きい）のみ","同名・別内容（比較側が大きい）のみ","同名・別内容（同サイズ）のみ","サイズ差分候補のみ","選択中のみ","削除予定のみ","更新予定のみ","未設定のみ"])
        cmb.pack(side="left", padx=(6, 14))
        cmb.bind("<<ComboboxSelected>>", self.on_filter_changed)
        ttk.Label(search, text="検索:").pack(side="left")
        ent = ttk.Entry(search, textvariable=self.search_var, width=34)
        ent.pack(side="left", padx=(6, 6))
        ent.bind("<KeyRelease>", lambda e: self.on_filter_changed())
        ttk.Button(search, text="検索をクリア", command=self.clear_search).pack(side="left")

        prog = ttk.Frame(self.outer, style="Card.TFrame", padding=12)
        prog.pack(fill="x", pady=(0, 10))
        line1 = ttk.Frame(prog)
        line1.pack(fill="x")
        ttk.Label(line1, textvariable=self.status_var).pack(side="left")
        ttk.Label(line1, textvariable=self.progress_label_var).pack(side="right")
        self.progress = ttk.Progressbar(prog, mode="determinate", maximum=100, style="Green.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=8)
        line2 = ttk.Frame(prog)
        line2.pack(fill="x")
        ttk.Label(line2, textvariable=self.eta_var).pack(side="left")
        ttk.Label(line2, textvariable=self.summary_var).pack(side="right")

        body = ttk.Panedwindow(self.outer, orient="horizontal")
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body, style="Card.TFrame", padding=8)
        right = ttk.Frame(body, style="Card.TFrame", padding=10)
        body.add(left, weight=3)
        body.add(right, weight=2)

        self.tree = ttk.Treeview(left, columns=self.column_order, show="headings", selectmode="extended")
        self._apply_tree_columns()
        ys = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        xs = ttk.Scrollbar(left, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        # 薄い背景色で分類を見分けやすくしつつ、文字の可読性を落とさない配色
        self.tree.tag_configure("same", background="#edf4ff")
        self.tree.tag_configure("same_name_same_size", background="#f2efff")
        self.tree.tag_configure("name_diff_target_large", background="#fff3e8")
        self.tree.tag_configure("name_diff_compare_large", background="#ffeef2")
        self.tree.tag_configure("name_diff_same_size", background="#f7f3ea")
        self.tree.tag_configure("size_diff", background="#eefaf0")
        self.tree.tag_configure("update", background="#fff7e6")
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<ButtonPress-1>", self.on_header_press, add="+")
        self.tree.bind("<ButtonRelease-1>", self.on_header_release, add="+")

        page_bar = ttk.Frame(left)
        page_bar.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(page_bar, text="前へ", command=self.prev_page).pack(side="left")
        ttk.Label(page_bar, textvariable=self.page_info_var).pack(side="left", padx=8)
        ttk.Button(page_bar, text="次へ", command=self.next_page).pack(side="left")

        ttk.Label(right, text="詳細", font=("Yu Gothic UI", 13, "bold")).pack(anchor="w")
        action = ttk.Frame(right)
        action.pack(fill="x", pady=(6, 8))
        ttk.Label(action, text="選択中の処理:").pack(side="left")
        self.action_combo = ttk.Combobox(action, textvariable=self.action_var, state="readonly", width=32, values=["選択側のファイルをゴミ箱へ移動","選択側のファイルで更新（移動）","何もしない"])
        self.action_combo.pack(side="left", padx=(6, 6))
        self.action_combo.bind("<<ComboboxSelected>>", self.on_action_selected)
        ttk.Button(action, text="この項目を選択解除", command=self.clear_current_selection).pack(side="left")

        detail_frame = ttk.Frame(right)
        detail_frame.pack(fill="both", expand=False, pady=(0, 8))
        self.detail_info = tk.Text(detail_frame, height=14, wrap="word", font=("Yu Gothic UI", 10), state="disabled")
        d_ys = ttk.Scrollbar(detail_frame, orient="vertical", command=self.detail_info.yview)
        d_xs = ttk.Scrollbar(detail_frame, orient="horizontal", command=self.detail_info.xview)
        self.detail_info.configure(yscrollcommand=d_ys.set, xscrollcommand=d_xs.set)
        self.detail_info.grid(row=0, column=0, sticky="nsew")
        d_ys.grid(row=0, column=1, sticky="ns")
        d_xs.grid(row=1, column=0, sticky="ew")
        detail_frame.rowconfigure(0, weight=1)
        detail_frame.columnconfigure(0, weight=1)

        ttk.Label(right, text="本文・差分プレビュー", font=("Yu Gothic UI", 13, "bold")).pack(anchor="w")
        diff_frame = ttk.Frame(right)
        diff_frame.pack(fill="both", expand=True, pady=(6, 0))
        self.diff_text = tk.Text(diff_frame, height=18, wrap="none", font=("Consolas", 9), state="disabled")
        f_ys = ttk.Scrollbar(diff_frame, orient="vertical", command=self.diff_text.yview)
        f_xs = ttk.Scrollbar(diff_frame, orient="horizontal", command=self.diff_text.xview)
        self.diff_text.configure(yscrollcommand=f_ys.set, xscrollcommand=f_xs.set)
        self.diff_text.grid(row=0, column=0, sticky="nsew")
        f_ys.grid(row=0, column=1, sticky="ns")
        f_xs.grid(row=1, column=0, sticky="ew")
        diff_frame.rowconfigure(0, weight=1)
        diff_frame.columnconfigure(0, weight=1)

        ttk.Label(right, text="実行ログ", font=("Yu Gothic UI", 13, "bold")).pack(anchor="w", pady=(10, 0))
        self.log_notebook = ttk.Notebook(right)
        self.log_notebook.pack(fill="both", expand=True, pady=(6, 0))
        self.log_widgets = {}
        for key, title in [("all","すべて"),("success","成功"),("error","失敗"),("stopped","停止"),("skip","スキップ"),("info","情報")]:
            frame = ttk.Frame(self.log_notebook)
            self.log_notebook.add(frame, text=title)
            txt = tk.Text(frame, height=10, wrap="none", font=("Consolas", 9), state="disabled")
            ys2 = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
            xs2 = ttk.Scrollbar(frame, orient="horizontal", command=txt.xview)
            txt.configure(yscrollcommand=ys2.set, xscrollcommand=xs2.set)
            txt.grid(row=0, column=0, sticky="nsew")
            ys2.grid(row=0, column=1, sticky="ns")
            xs2.grid(row=1, column=0, sticky="ew")
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)
            self.log_widgets[key] = txt

        statusbar = ttk.Frame(self.outer)
        statusbar.pack(fill="x", pady=(8, 0))
        ttk.Label(statusbar, textvariable=self.statusbar_var).pack(side="left")

        self._sync_log_tabs()
        self._update_statusbar()
        self._update_run_buttons()

    # --- helper rows ---
    def _path_row(self, parent, row, label, var, cmd):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 10))
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=6)
        ttk.Button(parent, text="参照", command=cmd).grid(row=row, column=2, sticky="w", padx=(10, 0), pady=6)
        parent.grid_columnconfigure(1, weight=1)

    def _entry_row(self, parent, row, label, var):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 10))
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, columnspan=2, sticky="ew", pady=6)
        parent.grid_columnconfigure(1, weight=1)

    def _set_text(self, widget: tk.Text, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    # --- logs ---
    def _log(self, kind: str, message: str):
        self.log_manager.add(kind, message)
        self._sync_log_tabs()

    def _sync_log_tabs(self):
        for key, widget in self.log_widgets.items():
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", self.log_manager.get_text(key))
            widget.see("end")
            widget.configure(state="disabled")

    def clear_log(self):
        self.log_manager.clear()
        self._sync_log_tabs()

    # --- state / progress ---
    def _reset_progress_display(self):
        self.progress["value"] = 0
        self.progress_label_var.set("0%")
        self.eta_var.set("残り時間: --:--:--")

    def _apply_progress(self, percent, message, current, total):
        self.progress["value"] = percent
        self.progress_label_var.set(f"{percent}%")
        self.status_var.set(message)
        if self.start_time is None:
            self.start_time = time.time()
        elapsed = max(time.time() - self.start_time, 0.001)
        rate = current / elapsed
        remain = max(total - current, 0)
        remain_seconds = int(remain / rate) if rate > 0 else 0
        h = remain_seconds // 3600
        m = (remain_seconds % 3600) // 60
        s = remain_seconds % 60
        self.eta_var.set(f"残り時間: {h:02d}:{m:02d}:{s:02d}")

    def _set_busy_state(self, scanning=None, executing=None):
        if scanning is not None:
            self.is_scanning = scanning
        if executing is not None:
            self.is_executing = executing
        busy = self.is_scanning or self.is_executing
        state = "disabled" if busy else "normal"
        self.scan_btn.configure(state=state)
        self.preview_btn.configure(state=state)
        self.exec_btn.configure(state=state)
        self.pause_btn.configure(state="normal" if busy else "disabled")
        self.resume_btn.configure(state="normal" if busy else "disabled")
        self.stop_btn.configure(state="normal" if busy else "disabled")

    def pause_current(self):
        if self.is_scanning:
            self.scan_controller.pause()
            self.run_state_var.set("スキャン: 一時停止中")
            self._log("info", "スキャンを一時停止しました")
            self.status_var.set("スキャンを一時停止中です")
        elif self.is_executing:
            self.execute_controller.pause()
            self.run_state_var.set("実行: 一時停止中")
            self._log("info", "実行を一時停止しました")
            self.status_var.set("実行を一時停止中です")

    def resume_current(self):
        if self.is_scanning:
            self.scan_controller.resume()
            self.run_state_var.set("スキャン: 実行中")
            self._log("info", "スキャンを再開しました")
            self.status_var.set("スキャンを再開しました")
        elif self.is_executing:
            self.execute_controller.resume()
            self.run_state_var.set("実行: 実行中")
            self._log("info", "実行を再開しました")
            self.status_var.set("実行を再開しました")

    def stop_current(self):
        if self.is_scanning:
            self.scan_controller.stop()
            self.run_state_var.set("スキャン: 停止要求中")
            self._log("stopped", "スキャン停止を要求しました")
        elif self.is_executing:
            self.execute_controller.stop()
            self.run_state_var.set("実行: 停止要求中")
            self._log("stopped", "実行停止を要求しました")

    # --- queues ---
    def _poll_queues(self):
        try:
            while True:
                kind, payload = self.scan_queue.get_nowait()
                if kind == "progress":
                    self._apply_progress(*payload)
                elif kind == "done":
                    self._scan_finished(*payload)
                elif kind == "error":
                    self._scan_failed(payload)
        except queue.Empty:
            pass

        try:
            while True:
                kind, payload = self.execute_queue.get_nowait()
                if kind == "progress":
                    self._apply_progress(*payload)
                elif kind == "done":
                    self._execute_finished(*payload)
                elif kind == "error":
                    self._execute_failed(payload)
        except queue.Empty:
            pass

        self.root.after(80, self._poll_queues)

    # --- tree / filters ---
    def _update_statusbar(self):
        target_count = sum(1 for x in self.scan_items if x.target_selected)
        compare_count = sum(1 for x in self.scan_items if x.compare_selected)
        planned_count = sum(1 for x in self.scan_items if (x.target_selected or x.compare_selected) and x.preferred_action != "何もしない")
        self.statusbar_var.set(f"対象側選択 {target_count}件 / 比較側選択 {compare_count}件 / 実行予定 {planned_count}件 / 最終スキャン {self.last_scan_time}")

    def _update_run_buttons(self):
        checked = [x for x in self.scan_items if x.target_selected or x.compare_selected]
        selected = [x for x in checked if x.preferred_action != "何もしない"]
        self.preview_btn.configure(text=f"2. 変更内容を確認（{len(selected)}件）")
        self.exec_btn.configure(text=f"3. 実行（{len(selected)}件）")

    def _save_column_widths(self):
        try:
            self.column_widths = {c: int(self.tree.column(c, "width")) for c in self.column_order}
        except Exception:
            pass

    def _apply_tree_columns(self):
        self.tree["displaycolumns"] = self.column_order
        self.tree["columns"] = self.column_order
        for c in self.column_order:
            width = int(self.column_widths.get(c, self.COLUMN_MIN_WIDTH.get(c, 100)))
            default_reverse = self.current_sort_reverse if self.current_sort_column == c else False
            self.tree.heading(c, text=self.COLUMN_LABELS[c], command=lambda col=c, rev=default_reverse: self.sort_tree_by(col, not rev))
            self.tree.column(c, width=width, anchor="w", stretch=True)
        display_values = [self.COLUMN_LABELS[c] for c in self.column_order]
        self.column_picker["values"] = display_values
        self.sort_picker["values"] = display_values
        if self.column_order and self.column_pick_var.get() not in display_values:
            self.column_pick_var.set(self.COLUMN_LABELS[self.column_order[0]])

    def apply_sort_from_picker(self):
        label = self.column_pick_var.get().strip()
        col = next((k for k, v in self.COLUMN_LABELS.items() if v == label), None)
        if not col:
            return
        reverse = self.sort_direction_var.get() == "降順"
        self.sort_tree_by(col, reverse)

    def clear_sort(self):
        self.current_sort_column = None
        self.current_sort_reverse = False
        self.sort_label_var.set("並び替えなし")
        self.refresh_tree()

    def reset_columns_to_default(self):
        self.column_order = self.DEFAULT_COLUMNS[:]
        self._apply_tree_columns()
        self.refresh_tree()
        self._log("info", "列順を初期状態に戻しました")

    def move_column_left(self):
        label = self.column_pick_var.get().strip()
        col = next((k for k, v in self.COLUMN_LABELS.items() if v == label), None)
        if not col:
            return
        idx = self.column_order.index(col)
        if idx == 0:
            return
        self.column_order[idx - 1], self.column_order[idx] = self.column_order[idx], self.column_order[idx - 1]
        self._apply_tree_columns()
        self.refresh_tree()

    def move_column_right(self):
        label = self.column_pick_var.get().strip()
        col = next((k for k, v in self.COLUMN_LABELS.items() if v == label), None)
        if not col:
            return
        idx = self.column_order.index(col)
        if idx >= len(self.column_order) - 1:
            return
        self.column_order[idx + 1], self.column_order[idx] = self.column_order[idx], self.column_order[idx + 1]
        self._apply_tree_columns()
        self.refresh_tree()

    def on_header_press(self, event):
        if self.tree.identify("region", event.x, event.y) != "heading":
            self.drag_col = None
            return
        col_id = self.tree.identify_column(event.x)
        cols = list(self.tree["displaycolumns"])
        idx = int(col_id.replace("#", "")) - 1 if col_id else -1
        self.drag_col = cols[idx] if 0 <= idx < len(cols) else None

    def on_header_release(self, event):
        if not self.drag_col:
            return
        try:
            if self.tree.identify("region", event.x, event.y) != "heading":
                return
            col_id = self.tree.identify_column(event.x)
            cols = list(self.tree["displaycolumns"])
            idx = int(col_id.replace("#", "")) - 1 if col_id else -1
            if not (0 <= idx < len(cols)):
                return
            target_col = cols[idx]
            if target_col != self.drag_col:
                old = self.column_order.index(self.drag_col)
                new = self.column_order.index(target_col)
                col = self.column_order.pop(old)
                self.column_order.insert(new, col)
                self._apply_tree_columns()
                self.refresh_tree()
        finally:
            self.drag_col = None
            self._save_column_widths()

    def clear_search(self):
        self.search_var.set("")
        self._reset_page_and_refresh()


    def on_filter_changed(self, _event=None):
        self.page = 1
        self.refresh_tree()

    def _passes_filter(self, row: ScanItem):
        mode = self.filter_var.get()
        if mode == "同一ファイルのみ" and row.category != "同一ファイル":
            return False
        if mode == "更新候補のみ" and row.category != "更新候補":
            return False
        if mode == "同名・同サイズのみ" and row.category != "同名・同サイズ":
            return False
        if mode == "同名・別内容（対象側が大きい）のみ" and row.category != "同名・別内容（対象側が大きい）":
            return False
        if mode == "同名・別内容（比較側が大きい）のみ" and row.category != "同名・別内容（比較側が大きい）":
            return False
        if mode == "同名・別内容（同サイズ）のみ" and row.category != "同名・別内容（同サイズ）":
            return False
        if mode == "サイズ差分候補のみ" and row.category != "サイズ差分候補":
            return False
        if mode == "選択中のみ" and not (row.target_selected or row.compare_selected):
            return False
        if mode == "削除予定のみ" and row.preferred_action != "選択側のファイルをゴミ箱へ移動":
            return False
        if mode == "更新予定のみ" and row.preferred_action not in ("選択側のファイルで更新", "選択側のファイルで更新（移動）"):
            return False
        if mode == "未設定のみ" and row.preferred_action != "何もしない":
            return False
        q = self.search_var.get().strip().lower()
        if q:
            merged = " ".join([
                row.category, row.confidence, row.preferred_action, row.reason, row.scope,
                row.target_path, row.compare_path, row.notes, str(row.target_size), str(row.compare_size)
            ]).lower()
            if q not in merged:
                return False
        return True

    def _row_values(self, row: ScanItem):
        return {
            "target_selected": "☑" if row.target_selected else "☐",
            "compare_selected": "☑" if row.compare_selected else "☐",
            "category": row.category,
            "confidence": row.confidence,
            "action": row.preferred_action,
            "target_size": bytes_text(row.target_size),
            "compare_size": bytes_text(row.compare_size),
            "reason": row.reason,
            "scope": row.scope,
            "target": self._short_path(row.target_path),
            "compare": self._short_path(row.compare_path),
        }

    def _short_path(self, value, max_len=52):
        return value if len(value) <= max_len else "..." + value[-(max_len - 3):]

    def _recompute_filtered_indices(self):
        self.filtered_indices = [i for i, row in enumerate(self.scan_items) if self._passes_filter(row)]
        total_pages = max(math.ceil(len(self.filtered_indices) / self.PAGE_SIZE), 1)
        self.page = min(max(1, self.page), total_pages)
        self.page_info_var.set(f"{self.page} / {total_pages}")

    def _reset_page_and_refresh(self):
        self.page = 1
        self.refresh_tree()

    def refresh_tree(self):
        current_selection = self.tree.selection()
        self._recompute_filtered_indices()
        start = (self.page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        page_indices = self.filtered_indices[start:end]

        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for idx in page_indices:
            row = self.scan_items[idx]
            tag = "same"
            if row.category == "更新候補":
                tag = "update"
            elif row.category == "同名・同サイズ":
                tag = "same_name_same_size"
            elif row.category == "同名・別内容（対象側が大きい）":
                tag = "name_diff_target_large"
            elif row.category == "同名・別内容（比較側が大きい）":
                tag = "name_diff_compare_large"
            elif row.category == "同名・別内容（同サイズ）":
                tag = "name_diff_same_size"
            elif row.category == "サイズ差分候補":
                tag = "size_diff"
            vals = self._row_values(row)
            self.tree.insert("", "end", iid=str(idx), values=[vals[c] for c in self.column_order], tags=(tag,))

        kept = [iid for iid in current_selection if self.tree.exists(iid)]
        if kept:
            self.tree.selection_set(kept)
            self.tree.focus(kept[-1])
        elif self.tree.get_children():
            first = self.tree.get_children()[0]
            self.tree.selection_set((first,))
            self.tree.focus(first)

        self.auto_fit_columns(sample_only=True)
        self.on_tree_select()
        self._update_statusbar()
        self._update_run_buttons()

    def auto_fit_columns(self, sample_only=False):
        try:
            fnt = tkfont.nametofont(str(self.tree.cget("font")))
        except Exception:
            fnt = tkfont.nametofont("TkDefaultFont")
        rows = self.tree.get_children()
        if sample_only:
            rows = rows[:80]
        for col in self.column_order:
            width = fnt.measure(self.COLUMN_LABELS[col]) + 24
            for iid in rows:
                width = max(width, fnt.measure(str(self.tree.set(iid, col))) + 24)
            width = min(max(width, self.COLUMN_MIN_WIDTH.get(col, 80)), 480)
            self.tree.column(col, width=width)
        self._save_column_widths()

    def sort_tree_by(self, column, reverse):
        mapping = {
            "target_selected": lambda x: 1 if x.target_selected else 0,
            "compare_selected": lambda x: 1 if x.compare_selected else 0,
            "category": lambda x: x.category,
            "confidence": lambda x: {"低": 1, "中": 2, "高": 3}.get(x.confidence, 0),
            "action": lambda x: x.preferred_action,
            "target_size": lambda x: x.target_size,
            "compare_size": lambda x: x.compare_size,
            "reason": lambda x: x.reason,
            "scope": lambda x: x.scope,
            "target": lambda x: x.target_path,
            "compare": lambda x: x.compare_path,
        }
        self.scan_items.sort(key=mapping.get(column, lambda x: x.category), reverse=reverse)
        self.current_sort_column = column
        self.current_sort_reverse = reverse
        self.column_pick_var.set(self.COLUMN_LABELS.get(column, self.column_pick_var.get()))
        self.sort_direction_var.set("降順" if reverse else "昇順")
        self.sort_label_var.set(f"現在のソート: {self.COLUMN_LABELS.get(column, column)} / {'降順' if reverse else '昇順'}")
        self.page = 1
        self.refresh_tree()

    def on_tree_click(self, event):
        if self.tree.identify("region", event.x, event.y) != "cell":
            return
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id:
            return
        index = int(item_id)
        cols = list(self.tree["displaycolumns"])
        disp_index = int(column.replace("#", "")) - 1
        if not (0 <= disp_index < len(cols)):
            return
        logical_col = cols[disp_index]
        if logical_col == "target_selected":
            self.scan_items[index].target_selected = not self.scan_items[index].target_selected
            if self.scan_items[index].target_selected:
                self.scan_items[index].compare_selected = False
            self.refresh_tree()
            self.tree.selection_set((item_id,))
            self.show_detail([index])
            return "break"
        if logical_col == "compare_selected":
            self.scan_items[index].compare_selected = not self.scan_items[index].compare_selected
            if self.scan_items[index].compare_selected:
                self.scan_items[index].target_selected = False
            self.refresh_tree()
            self.tree.selection_set((item_id,))
            self.show_detail([index])
            return "break"

    def on_tree_select(self, _event=None):
        ids = [int(i) for i in self.tree.selection() if i.isdigit()]
        self.current_detail_indices = ids
        self.show_detail(ids)

    def on_action_selected(self, _event=None):
        value = self.action_var.get().strip()
        if not value:
            return
        checked = [i for i, item in enumerate(self.scan_items) if item.target_selected or item.compare_selected]
        ids = checked if checked else self.current_detail_indices
        if not ids:
            return
        for idx in ids:
            self.scan_items[idx].preferred_action = value
        self.refresh_tree()
        keep = tuple(str(i) for i in ids if self.tree.exists(str(i)))
        if keep:
            self.tree.selection_set(keep)
        self.show_detail(ids)

    def show_detail(self, indices):
        if not indices:
            self._set_text(self.detail_info, "")
            self._set_text(self.diff_text, "")
            self.action_var.set("何もしない")
            return
        valid = [i for i in indices if 0 <= i < len(self.scan_items)]
        if not valid:
            return

        if len(valid) == 1:
            item = self.scan_items[valid[0]]
            self.action_var.set(item.preferred_action)
            lines = [
                f"種類: {item.category}",
                f"信頼度: {item.confidence}",
                f"現在の処理: {item.preferred_action}",
                f"理由: {item.reason}",
                f"範囲: {item.scope}",
                f"選択状態: {item.selection_state_text()}",
                "",
                "対象側ファイル:",
                f"  {item.target_path}",
                f"  サイズ: {bytes_text(item.target_size)}",
                f"  更新日時: {datetime.fromtimestamp(item.target_mtime).strftime('%Y-%m-%d %H:%M:%S') if item.target_mtime else '-'}",
                "",
                "比較側ファイル:",
                f"  {item.compare_path}",
                f"  サイズ: {bytes_text(item.compare_size)}",
                f"  更新日時: {datetime.fromtimestamp(item.compare_mtime).strftime('%Y-%m-%d %H:%M:%S') if item.compare_mtime else '-'}",
                "",
                f"本文の近さ: {item.similarity * 100:.1f}%",
                f"差分要約: {item.diff_summary}",
                f"補足: {item.notes}",
            ]
            self._set_text(self.detail_info, "\n".join(lines))
            a = read_text_preview(item.target_path, max_chars=1800)
            b = read_text_preview(item.compare_path, max_chars=1800)
            diff_lines = list(difflib.unified_diff(a.splitlines(), b.splitlines(), fromfile="対象側", tofile="比較側", lineterm=""))
            text = ("差分が見つからないか、本文比較対象外です。\n\n" if not diff_lines else "\n".join(diff_lines[:300]) + "\n\n")
            text += "---- 対象側プレビュー ----\n" + a[:2000] + "\n\n"
            text += "---- 比較側プレビュー ----\n" + b[:2000]
            self._set_text(self.diff_text, text)
            return

        items = [self.scan_items[i] for i in valid]
        target_count = sum(1 for x in items if x.target_selected)
        compare_count = sum(1 for x in items if x.compare_selected)
        total_target = sum(max(0, x.target_size) for x in items)
        total_compare = sum(max(0, x.compare_size) for x in items)
        categories = {}
        actions = {}
        for item in items:
            categories[item.category] = categories.get(item.category, 0) + 1
            actions[item.preferred_action] = actions.get(item.preferred_action, 0) + 1
        self.action_var.set(next(iter(actions.keys())) if len(actions) == 1 else "何もしない")
        lines = [
            f"複数選択: {len(items)}件",
            f"対象側チェック: {target_count}件",
            f"比較側選択: {compare_count}件",
            f"対象側サイズ合計: {bytes_text(total_target)}",
            f"比較側サイズ合計: {bytes_text(total_compare)}",
            "",
            "種類ごとの件数:",
        ]
        for k, v in categories.items():
            lines.append(f"  ・{k}: {v}件")
        lines.append("")
        lines.append("現在の処理ごとの件数:")
        for k, v in actions.items():
            lines.append(f"  ・{k}: {v}件")
        lines.append("")
        lines.append("※ 右上のプルダウンで、複数選択中の項目へ同じ処理を一括設定できます。")
        self._set_text(self.detail_info, "\n".join(lines))

        preview_lines = ["複数選択中のため、本文差分は個別表示ではなく一覧要約を表示しています。", ""]
        for idx, item in enumerate(items[:20], start=1):
            preview_lines.append(f"[{idx}] {item.category} / {item.selection_state_text()} / {item.reason}")
            preview_lines.append(f"    対象側サイズ: {bytes_text(item.target_size)} / 比較側サイズ: {bytes_text(item.compare_size)}")
            preview_lines.append(f"    対象側: {item.target_path}")
            preview_lines.append(f"    比較側: {item.compare_path}")
        if len(items) > 20:
            preview_lines.append("")
            preview_lines.append(f"…他 {len(items)-20} 件")
        self._set_text(self.diff_text, "\n".join(preview_lines))

    # --- selection ---
    def clear_current_selection(self):
        for idx in self.current_detail_indices:
            self.scan_items[idx].target_selected = False
            self.scan_items[idx].compare_selected = False
        self.refresh_tree()

    def select_all_target(self):
        visible_indices = [idx for idx, row in enumerate(self.scan_items) if self._passes_filter(row)]
        for idx in visible_indices:
            row = self.scan_items[idx]
            row.target_selected = True
            row.compare_selected = False
        self.refresh_tree()

    def select_all_compare(self):
        visible_indices = [idx for idx, row in enumerate(self.scan_items) if self._passes_filter(row)]
        for idx in visible_indices:
            row = self.scan_items[idx]
            row.compare_selected = bool(row.compare_path)
            row.target_selected = False if row.compare_selected else True
        self.refresh_tree()

    def clear_target_selection(self):
        visible_indices = [idx for idx, row in enumerate(self.scan_items) if self._passes_filter(row)]
        for idx in visible_indices:
            row = self.scan_items[idx]
            row.target_selected = False
        self.refresh_tree()

    def clear_compare_selection(self):
        visible_indices = [idx for idx, row in enumerate(self.scan_items) if self._passes_filter(row)]
        for idx in visible_indices:
            row = self.scan_items[idx]
            row.compare_selected = False
        self.refresh_tree()

    def clear_all_selection(self):
        visible_indices = [idx for idx, row in enumerate(self.scan_items) if self._passes_filter(row)]
        for idx in visible_indices:
            row = self.scan_items[idx]
            row.target_selected = False
            row.compare_selected = False
        self.refresh_tree()

    def _folder_size_totals(self):
        return int(self.last_scan_summary.get("source_bytes", 0)), int(self.last_scan_summary.get("compare_bytes", 0))

    def select_smaller_side(self):
        if not self.scan_items:
            return
        visible_indices = [idx for idx, row in enumerate(self.scan_items) if self._passes_filter(row)]
        if not visible_indices:
            return

        for idx in visible_indices:
            row = self.scan_items[idx]
            target_size = max(0, int(getattr(row, "target_size", 0) or 0))
            compare_size = max(0, int(getattr(row, "compare_size", 0) or 0))

            if row.compare_path:
                if target_size <= compare_size:
                    row.target_selected = True
                    row.compare_selected = False
                else:
                    row.target_selected = False
                    row.compare_selected = True
            else:
                row.target_selected = True
                row.compare_selected = False
        self.refresh_tree()

    def select_larger_side(self):
        if not self.scan_items:
            return
        visible_indices = [idx for idx, row in enumerate(self.scan_items) if self._passes_filter(row)]
        if not visible_indices:
            return

        for idx in visible_indices:
            row = self.scan_items[idx]
            target_size = max(0, int(getattr(row, "target_size", 0) or 0))
            compare_size = max(0, int(getattr(row, "compare_size", 0) or 0))

            if row.compare_path:
                if target_size >= compare_size:
                    row.target_selected = True
                    row.compare_selected = False
                else:
                    row.target_selected = False
                    row.compare_selected = True
            else:
                row.target_selected = True
                row.compare_selected = False
        self.refresh_tree()

    def prev_page(self):



        if self.page > 1:
            self.page -= 1
            self.refresh_tree()

    def next_page(self):
        total_pages = max(math.ceil(len(self.filtered_indices) / self.PAGE_SIZE), 1)
        if self.page < total_pages:
            self.page += 1
            self.refresh_tree()

    # --- scan / execute / validation ---
    def _validate_before_execute(self, items: list[ScanItem]):
        errors = []
        warnings = []
        for item in items:
            if item.target_selected and item.compare_selected:
                errors.append(f"両側選択: {item.target_path}")
                continue
            if not item.target_selected and not item.compare_selected:
                errors.append(f"未選択: {item.target_path}")
                continue
            if item.preferred_action not in ("選択側のファイルをゴミ箱へ移動", "選択側のファイルで更新", "選択側のファイルで更新（移動）"):
                warnings.append(f"処理未設定: {item.target_path}")
                continue

            selected_path = item.target_path if item.target_selected else item.compare_path
            other_path = item.compare_path if item.target_selected else item.target_path

            if not os.path.exists(selected_path):
                errors.append(f"選択側ファイルが見つかりません: {selected_path}")
            if item.preferred_action == "選択側のファイルで更新" and not os.path.exists(other_path):
                errors.append(f"更新先または相手側ファイルが見つかりません: {other_path}")
            if os.path.abspath(selected_path) == os.path.abspath(other_path):
                errors.append(f"同じファイルを相手として処理しようとしています: {selected_path}")
            if item.preferred_action == "選択側のファイルで更新":
                parent = os.path.dirname(other_path)
                if parent and not os.access(parent, os.W_OK):
                    warnings.append(f"更新先フォルダへ書き込みできない可能性があります: {parent}")
        return errors, warnings

    def scan(self):
        if self.is_scanning or self.is_executing:
            return
        source = self.source_var.get().strip()
        compare = self.compare_var.get().strip()
        if not source:
            messagebox.showwarning("未入力", "対象フォルダを選択してください。")
            return
        if not os.path.isdir(source):
            messagebox.showerror("エラー", "対象フォルダが見つかりません。")
            return
        if compare and not os.path.isdir(compare):
            messagebox.showerror("エラー", "比較フォルダが見つかりません。")
            return

        self.scan_controller.reset()
        self.start_time = time.time()
        self.progress["value"] = 0
        self.progress_label_var.set("0%")
        self.eta_var.set("残り時間: 計算中")
        self.status_var.set("スキャンを開始します")
        self.run_state_var.set("スキャン: 実行中")
        self._log("info", "スキャン開始")
        self._set_busy_state(scanning=True)

        def progress_cb(current, total, message):
            self.scan_controller.check()
            total = max(total, 1)
            self.scan_queue.put(("progress", (int((current / total) * 100), message, current, total)))

        def worker():
            try:
                items, summary = scan_folders(
                    source_dir=source,
                    compare_dir=compare or None,
                    exclude_dirs=self._exclude_dirs(),
                    exclude_exts=self._exclude_exts(),
                    progress_cb=progress_cb,
                )
                self.scan_queue.put(("done", (items, summary)))
            except Exception as e:
                self.scan_queue.put(("error", e))

        threading.Thread(target=worker, daemon=True).start()

    def _scan_finished(self, items, summary):
        self.scan_items = items
        self.last_scan_summary = summary
        self.last_scan_time = datetime.now().strftime("%H:%M:%S")
        self.summary_var.set(
            f"対象フォルダ {summary['source_files']}件 / 比較フォルダ {summary['compare_files']}件 / "
            f"ファイル数比較 {summary.get('file_count_winner', '--')} / "
            f"対象側画像 {summary.get('source_image_files', 0)}件(+zip内{summary.get('source_zip_image_files', 0)}件) / "
            f"比較側画像 {summary.get('compare_image_files', 0)}件(+zip内{summary.get('compare_zip_image_files', 0)}件) / "
            f"同一 {summary['same_items']}件 / 更新候補 {summary['update_items']}件 / "
            f"同名同サイズ {summary.get('same_name_same_size_items', 0)}件 / "
            f"同名別内容(対象側大) {summary.get('same_name_diff_target_large_items', 0)}件 / "
            f"同名別内容(比較側大) {summary.get('same_name_diff_compare_large_items', 0)}件 / "
            f"同名別内容(同サイズ) {summary.get('same_name_diff_same_size_items', 0)}件 / "
            f"サイズ差分 {summary['size_diff_items']}件"
        )
        self.status_var.set("スキャンが完了しました")
        self.run_state_var.set("待機中")
        self.progress["value"] = 100
        self.progress_label_var.set("100%")
        self.page = 1
        self.refresh_tree()
        self._set_busy_state(scanning=False)
        self._log("success", f"スキャン完了: 候補 {summary['total_items']}件")
        if not self.scan_items:
            messagebox.showinfo("結果", "該当する候補は見つかりませんでした。")
        self.root.after(800, self._reset_progress_display)

    def _scan_failed(self, error):
        self.status_var.set("スキャンは終了しました")
        self.run_state_var.set("待機中")
        self._set_busy_state(scanning=False)
        self._reset_progress_display()
        if isinstance(error, InterruptedError):
            self._log("stopped", "スキャンを停止しました")
            messagebox.showinfo("停止", "スキャンを停止しました。")
        else:
            self._log("error", f"スキャン失敗: {error}")
            messagebox.showerror("エラー", f"スキャン中に問題が発生しました。\n{error}")

    def preview_changes(self):
        checked = [x for x in self.scan_items if x.target_selected or x.compare_selected]
        if not checked:
            messagebox.showinfo("確認", "現在、実行対象に選ばれている項目はありません。")
            return
        selected = [x for x in checked if x.preferred_action != "何もしない"]
        unspecified = len(checked) - len(selected)
        if not selected and unspecified > 0:
            messagebox.showwarning("処理未指定", "チェック済みの項目はありますが、処理内容が指定されていません。\n右側の『選択中の処理』で、チェック済み項目へ一括指定してください。")
            return

        counts = {}
        total_target = 0
        total_compare = 0
        for x in selected:
            side = "対象側" if x.target_selected else "比較側"
            key = f"{side}: {x.preferred_action}"
            counts[key] = counts.get(key, 0) + 1
            total_target += max(0, x.target_size)
            total_compare += max(0, x.compare_size)

        lines = ["この確認では、まだ実際の変更は行いません。", "", f"選択中の件数: {len(selected)}件", f"対象側サイズ合計: {bytes_text(total_target)}", f"比較側サイズ合計: {bytes_text(total_compare)}"]
        if self.last_scan_summary:
            lines.append(f"ファイル数が多い側: {self.last_scan_summary.get('file_count_winner', '--')}")
            lines.append(f"対象側画像数: {self.last_scan_summary.get('source_image_files', 0)}件（zip内 {self.last_scan_summary.get('source_zip_image_files', 0)}件）")
            lines.append(f"比較側画像数: {self.last_scan_summary.get('compare_image_files', 0)}件（zip内 {self.last_scan_summary.get('compare_zip_image_files', 0)}件）")
        lines += ["", "実行予定の処理:"]
        for k, v in counts.items():
            lines.append(f"  ・{k}: {v}件")
        if unspecified > 0:
            lines.append(f"  ・処理未指定: {unspecified}件")
        lines += ["", "ゴミ箱移動や更新は実行時に警告が出ます。"]
        messagebox.showinfo("変更内容の確認", "\n".join(lines))

    def _confirm_dangerous_actions(self, selected):
        trash = sum(1 for x in selected if x.preferred_action == "選択側のファイルをゴミ箱へ移動")
        update = sum(1 for x in selected if x.preferred_action in ("選択側のファイルで更新", "選択側のファイルで更新（移動）"))
        if trash:
            if not messagebox.askyesno("警告: ゴミ箱移動を含みます", f"ゴミ箱移動を含む処理が {trash} 件あります。\n続行しますか？"):
                return False
        if update:
            if not messagebox.askyesno("警告: 上書き更新を含みます", f"上書き更新を含む処理が {update} 件あります。\n現在の内容は置き換わります。\n本当に続行しますか？"):
                return False
        return True

    def execute(self):
        if self.is_scanning or self.is_executing:
            return
        checked = [x for x in self.scan_items if x.target_selected or x.compare_selected]
        if not checked:
            messagebox.showwarning("未選択", "実行対象がありません。")
            return
        selected = [x for x in checked if x.preferred_action != "何もしない"]
        unspecified = len(checked) - len(selected)
        if not selected:
            messagebox.showwarning("処理未指定", "チェック済みの項目に処理内容が指定されていません。\n右側の『選択中の処理』で、チェック済み項目へ一括指定してください。")
            return

        errors, warnings = self._validate_before_execute(selected)
        if errors:
            messagebox.showerror("実行前検証エラー", "\n".join(errors[:20]))
            return
        if warnings:
            messagebox.showwarning("実行前検証の注意", "\n".join(warnings[:20]))

        dialog = ConfirmationDialog(self.root, selected)
        self.root.wait_window(dialog)
        if not dialog.result:
            return

        counts = {}
        for x in selected:
            side = "対象側" if x.target_selected else "比較側"
            counts[f"{side}: {x.preferred_action}"] = counts.get(f"{side}: {x.preferred_action}", 0) + 1

        msg = ["次の内容を実行します。", ""]
        for k, v in counts.items():
            msg.append(f"・{k}: {v}件")
        if unspecified > 0:
            msg.append(f"・処理未指定: {unspecified}件（実行対象外）")
        msg += ["", "実行しますか？"]
        if not messagebox.askyesno("最終確認", "\n".join(msg)):
            return
        if not self._confirm_dangerous_actions(selected):
            return

        self.execute_controller.reset()
        self._set_busy_state(executing=True)
        self.start_time = time.time()
        self.progress["value"] = 0
        self.progress_label_var.set("0%")
        self.eta_var.set("残り時間: 計算中")
        self.status_var.set("処理を実行中です")
        self.run_state_var.set("実行: 実行中")
        self._log("info", "実行開始")

        def progress_cb(current, total, message):
            self.execute_controller.check()
            total = max(total, 1)
            self.execute_queue.put(("progress", (int((current / total) * 100), message, current, total)))

        def worker():
            try:
                results, manifest_path = execute_items(selected, self.backup_manager, self.execute_controller, progress_cb)
                summary = {
                    "実行対象件数": len(selected),
                    "成功件数": sum(1 for r in results if r["status"] == "成功"),
                    "失敗件数": sum(1 for r in results if r["status"] == "失敗"),
                    "停止件数": sum(1 for r in results if r["status"] == "停止"),
                    "対象フォルダ": self.source_var.get().strip(),
                    "比較フォルダ": self.compare_var.get().strip(),
                    "バックアップ情報": manifest_path,
                }
                report_path = self.report_manager.save_report(summary, results)
                self.execute_queue.put(("done", (results, summary, report_path)))
            except Exception as e:
                self.execute_queue.put(("error", e))

        threading.Thread(target=worker, daemon=True).start()

    def _execute_finished(self, results, summary, report_path):
        self.status_var.set("処理が完了しました")
        self.run_state_var.set("待機中")
        if summary.get("停止件数", 0) == 0:
            self.progress["value"] = 100
        self._set_busy_state(executing=False)
        self._log("success", f"実行完了: 成功 {summary['成功件数']}件 / 失敗 {summary['失敗件数']}件 / 停止 {summary['停止件数']}件")
        self._log("info", f"レポート保存: {report_path}")
        for r in results:
            if r["status"] == "成功":
                if r.get("kind") == "スキップ":
                    self._log("skip", f"{r['action']} / {r['target']} / {r.get('message','')}")
                else:
                    self._log("success", f"{r['action']} / {r['target']} / {r.get('message','')}")
            elif r["status"] == "停止":
                self._log("stopped", f"{r.get('target','')}")
            else:
                self._log("error", f"{r['target']} / {r.get('error','不明なエラー')}")

        # 実行直後の一覧に、既に削除・更新済みの古いスキャン結果が残らないように一旦クリアして再描画する
        self.scan_items = []
        self.filtered_indices = []
        self.current_detail_indices = []
        self.refresh_tree()

        messagebox.showinfo("完了", f"処理が完了しました。\n成功: {summary['成功件数']}件\n失敗: {summary['失敗件数']}件\n停止: {summary['停止件数']}件\n\nレポート:\n{report_path}")
        self.root.after(800, self._reset_progress_display)
        self.scan()

    def _execute_failed(self, error):
        self.status_var.set("実行は終了しました")
        self.run_state_var.set("待機中")
        self._set_busy_state(executing=False)
        self._reset_progress_display()
        if isinstance(error, InterruptedError):
            self._log("stopped", "実行を停止しました")
            messagebox.showinfo("停止", "実行を停止しました。")
        else:
            self._log("error", f"実行失敗: {error}")
            messagebox.showerror("エラー", f"実行中に問題が発生しました。\n{error}")

    def undo_recent(self):
        sessions = self.backup_manager.list_recent_sessions(limit=3)
        if not sessions:
            messagebox.showinfo("元に戻す", "元に戻せるバックアップセッションがありません。")
            return
        dialog = UndoSelectDialog(self.root, sessions)
        self.root.wait_window(dialog)
        if not dialog.result_manifest_path:
            return
        if not messagebox.askyesno("元に戻す確認", "選択したセッションの更新・削除を元に戻します。実行しますか？"):
            return
        success, failed, messages = self.backup_manager.undo_session(dialog.result_manifest_path)
        for msg in messages:
            self._log("info" if ("戻しました" in msg or "更新前の状態に戻しました" in msg) else "error", msg)
        messagebox.showinfo("元に戻す", f"戻した件数: {success}件\n戻せなかった件数: {failed}件")
        if success or failed:
            self.scan()

    # --- basic ui actions ---
    def choose_source(self):
        path = filedialog.askdirectory(title="対象フォルダを選択")
        if path:
            self.source_var.set(path)

    def choose_compare(self):
        path = filedialog.askdirectory(title="比較フォルダを選択")
        if path:
            self.compare_var.set(path)

    def _exclude_dirs(self):
        return [x.strip() for x in self.exclude_dirs_var.get().split(",") if x.strip()]

    def _exclude_exts(self):
        values = [x.strip() for x in self.exclude_exts_var.get().split(",") if x.strip()]
        return [x if x.startswith(".") else f".{x}" for x in values]


    def _collect_settings_payload(self):
        self._save_column_widths()
        return {
            "last_source_dir": self.source_var.get().strip(),
            "last_compare_dir": self.compare_var.get().strip(),
            "window_geometry": self.root.geometry(),
            "filter_mode": self.filter_var.get(),
            "search_text": self.search_var.get(),
            "exclude_dirs": self._exclude_dirs(),
            "exclude_exts": self._exclude_exts(),
            "column_order": self.column_order[:],
            "column_widths": dict(self.column_widths),
            "page": self.page,
            "sort_column": self.current_sort_column,
            "sort_reverse": self.current_sort_reverse,
        }

    def _has_settings_changes(self):
        try:
            return self._collect_settings_payload() != getattr(self, "_settings_snapshot", {})
        except Exception:
            return True

    def save_settings(self):
        try:
            payload = self._collect_settings_payload()
            self.settings_manager.save(payload)
            self._settings_snapshot = payload
            self._log("info", "設定を保存しました")
            messagebox.showinfo("保存", "設定を保存しました。")
        except Exception as e:
            self._log("error", f"設定保存失敗: {e}")
            messagebox.showerror("エラー", f"設定保存に失敗しました。\n{e}")

    def on_close(self):
        try:
            if self._has_settings_changes():
                ans = messagebox.askyesno("設定の保存", "設定の変更があります。保存して閉じますか？")
                if ans:
                    payload = self._collect_settings_payload()
                    self.settings_manager.save(payload)
                    self._settings_snapshot = payload
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()
