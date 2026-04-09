from __future__ import annotations

import os
import time
import difflib
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk, font as tkfont

from .content_tools import read_text_preview
from .executor import execute_items
from .report_manager import ReportManager
from .scanner import ScanItem, scan_folders
from .settings_manager import SettingsManager


class FileManagerApp:
    DEFAULT_COLUMNS = [
        "target_selected", "compare_selected", "category", "confidence",
        "action", "reason", "scope", "target", "compare"
    ]
    COLUMN_LABELS = {
        "target_selected": "対象",
        "compare_selected": "比較",
        "category": "種類",
        "confidence": "信頼度",
        "action": "選択中の処理",
        "reason": "理由",
        "scope": "範囲",
        "target": "対象フォルダ側ファイル",
        "compare": "比較フォルダ側ファイル",
    }
    COLUMN_MIN_WIDTH = {
        "target_selected": 55,
        "compare_selected": 55,
        "category": 110,
        "confidence": 70,
        "action": 180,
        "reason": 180,
        "scope": 90,
        "target": 220,
        "compare": 220,
    }
    PAGE_SIZE = 1000

    def __init__(self) -> None:
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.settings_manager = SettingsManager(self.base_dir)
        self.report_manager = ReportManager(self.base_dir)
        self.settings = self.settings_manager.load()

        self.root = tk.Tk()
        self.root.title("ファイル管理ツール")
        self.root.geometry(self.settings.get("window_geometry", "1360x860"))
        self.root.minsize(1180, 760)

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self._apply_styles()

        self.source_var = tk.StringVar(value=self.settings.get("last_source_dir", ""))
        self.compare_var = tk.StringVar(value=self.settings.get("last_compare_dir", ""))
        self.status_var = tk.StringVar(value="フォルダを選択してスキャンしてください")
        self.progress_label_var = tk.StringVar(value="0%")
        self.eta_var = tk.StringVar(value="終了予測: --:--:--")
        self.summary_var = tk.StringVar(value="対象フォルダ 0件 / 比較フォルダ 0件 / 同一 0件 / 更新候補 0件 / 同名別内容 0件 / サイズ差分 0件")
        self.filter_var = tk.StringVar(value=self.settings.get("filter_mode", "すべて"))
        self.search_var = tk.StringVar(value=self.settings.get("search_text", ""))
        self.exclude_dirs_var = tk.StringVar(value=", ".join(self.settings.get("exclude_dirs", [])))
        self.exclude_exts_var = tk.StringVar(value=", ".join(self.settings.get("exclude_exts", [])))
        self.statusbar_var = tk.StringVar(value="対象側選択 0件 / 比較側選択 0件 / 実行予定 0件 / 最終スキャン --")
        self.action_var = tk.StringVar(value="何もしない")
        self.column_pick_var = tk.StringVar()
        self.page_var = tk.IntVar(value=1)

        saved_order = self.settings.get("column_order", self.DEFAULT_COLUMNS)
        self.column_order = [c for c in saved_order if c in self.DEFAULT_COLUMNS]
        for c in self.DEFAULT_COLUMNS:
            if c not in self.column_order:
                self.column_order.append(c)

        self.scan_items: list[ScanItem] = []
        self.filtered_indices: list[int] = []
        self.current_detail_indices: list[int] = []
        self.start_time = None
        self.log_lines: list[str] = []
        self.last_scan_time = "--"
        self.is_scanning = False
        self.drag_col = None

        self._build_scrollable_window()
        self._build_menu()
        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_scrollable_window(self) -> None:
        self.canvas = tk.Canvas(self.root, bg="#f3f6fb", highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self.root, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.outer = ttk.Frame(self.canvas, padding=14)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.outer, anchor="nw")
        self.outer.bind("<Configure>", self._on_outer_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_outer_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event=None) -> None:
        self.canvas.itemconfig(self.canvas_window, width=max(event.width, 1200))

    def _on_mousewheel(self, event) -> None:
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def _apply_styles(self) -> None:
        self.root.configure(bg="#f3f6fb")
        self.style.configure("Title.TLabel", font=("Yu Gothic UI", 18, "bold"), background="#f3f6fb")
        self.style.configure("Sub.TLabel", font=("Yu Gothic UI", 10), background="#f3f6fb", foreground="#506070")
        self.style.configure("Card.TFrame", relief="solid", borderwidth=1, background="#ffffff")
        self.style.configure("Accent.TButton", padding=(14, 8))
        self.style.configure("Treeview", rowheight=30, font=("Yu Gothic UI", 10))
        self.style.configure("Treeview.Heading", font=("Yu Gothic UI", 10, "bold"))
        self.style.map("Treeview", background=[("selected", "#ddeafc")])

    def _build_menu(self) -> None:
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
        menubar.add_cascade(label="操作", menu=action_menu)

        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_command(label="ログをクリア", command=self.clear_log)
        view_menu.add_command(label="列幅を自動調整", command=self.auto_fit_columns)
        menubar.add_cascade(label="表示", menu=view_menu)
        self.root.config(menu=menubar)

    def _build_layout(self) -> None:
        header = ttk.Frame(self.outer)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="ファイル管理ツール", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="対象フォルダと比較フォルダを比べて、選択した側をゴミ箱へ移動、または選択した側の内容で相手側を更新します。", style="Sub.TLabel").pack(anchor="w", pady=(4, 0))

        path_card = ttk.Frame(self.outer, style="Card.TFrame", padding=12)
        path_card.pack(fill="x", pady=(0, 10))
        self._path_row(path_card, 0, "対象フォルダ", self.source_var, self.choose_source)
        self._path_row(path_card, 1, "比較フォルダ（任意）", self.compare_var, self.choose_compare)
        self._simple_row(path_card, 2, "除外フォルダ", self.exclude_dirs_var)
        self._simple_row(path_card, 3, "除外拡張子", self.exclude_exts_var)

        toolbar = ttk.Frame(self.outer)
        toolbar.pack(fill="x", pady=(0, 10))
        self.scan_btn = ttk.Button(toolbar, text="1. スキャン", command=self.scan, style="Accent.TButton")
        self.scan_btn.pack(side="left")
        self.preview_btn = ttk.Button(toolbar, text="2. 変更内容を確認", command=self.preview_changes)
        self.preview_btn.pack(side="left", padx=8)
        self.exec_btn = ttk.Button(toolbar, text="3. 実行", command=self.execute)
        self.exec_btn.pack(side="left")
        ttk.Button(toolbar, text="件数が少ない側を全て選択", command=self.select_smaller_side).pack(side="left", padx=(18, 6))
        ttk.Button(toolbar, text="件数が多い側を全て選択", command=self.select_larger_side).pack(side="left", padx=6)
        ttk.Button(toolbar, text="対象フォルダを全て選択", command=self.select_all_target).pack(side="left", padx=6)
        ttk.Button(toolbar, text="比較フォルダを全て選択", command=self.select_all_compare).pack(side="left", padx=6)
        ttk.Button(toolbar, text="全て選択解除", command=self.clear_all_selection).pack(side="left", padx=6)

        column_toolbar = ttk.Frame(self.outer)
        column_toolbar.pack(fill="x", pady=(0, 10))
        ttk.Label(column_toolbar, text="一覧の並び:").pack(side="left")
        self.column_picker = ttk.Combobox(column_toolbar, textvariable=self.column_pick_var, state="readonly", width=24,
                                          values=[self.COLUMN_LABELS[c] for c in self.column_order])
        self.column_picker.pack(side="left", padx=(6, 6))
        ttk.Button(column_toolbar, text="← 左へ", command=self.move_column_left).pack(side="left")
        ttk.Button(column_toolbar, text="右へ →", command=self.move_column_right).pack(side="left", padx=6)
        ttk.Button(column_toolbar, text="列幅を自動調整", command=self.auto_fit_columns).pack(side="left", padx=12)
        ttk.Label(column_toolbar, text="※ 見出しドラッグでも並び替えできます。").pack(side="left", padx=8)

        search_bar = ttk.Frame(self.outer)
        search_bar.pack(fill="x", pady=(0, 10))
        ttk.Label(search_bar, text="表示:").pack(side="left")
        combo = ttk.Combobox(search_bar, textvariable=self.filter_var, state="readonly", width=20,
                             values=["すべて", "同一ファイルのみ", "更新候補のみ", "同名・別内容のみ", "サイズ差分候補のみ", "選択中のみ"])
        combo.pack(side="left", padx=(6, 14))
        combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_tree())
        ttk.Label(search_bar, text="検索:").pack(side="left")
        search_entry = ttk.Entry(search_bar, textvariable=self.search_var, width=34)
        search_entry.pack(side="left", padx=(6, 6))
        search_entry.bind("<KeyRelease>", lambda e: self.refresh_tree())
        ttk.Button(search_bar, text="検索をクリア", command=self.clear_search).pack(side="left")

        progress_card = ttk.Frame(self.outer, style="Card.TFrame", padding=12)
        progress_card.pack(fill="x", pady=(0, 10))
        top_line = ttk.Frame(progress_card)
        top_line.pack(fill="x")
        ttk.Label(top_line, textvariable=self.status_var).pack(side="left")
        ttk.Label(top_line, textvariable=self.progress_label_var).pack(side="right")
        self.progress = ttk.Progressbar(progress_card, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=8)
        bottom_line = ttk.Frame(progress_card)
        bottom_line.pack(fill="x")
        ttk.Label(bottom_line, textvariable=self.eta_var).pack(side="left")
        ttk.Label(bottom_line, textvariable=self.summary_var).pack(side="right")

        body = ttk.Panedwindow(self.outer, orient="horizontal")
        body.pack(fill="both", expand=True)
        left_card = ttk.Frame(body, style="Card.TFrame", padding=8)
        right_card = ttk.Frame(body, style="Card.TFrame", padding=10)
        body.add(left_card, weight=3)
        body.add(right_card, weight=2)

        self.tree = ttk.Treeview(left_card, columns=self.column_order, show="headings", selectmode="extended")
        self._apply_tree_columns()
        yscroll = ttk.Scrollbar(left_card, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(left_card, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        left_card.rowconfigure(0, weight=1)
        left_card.columnconfigure(0, weight=1)

        self.tree.tag_configure("same", background="#eef7ff")
        self.tree.tag_configure("update", background="#fff8e8")
        self.tree.tag_configure("name_diff", background="#fff1f1")
        self.tree.tag_configure("size_diff", background="#eefaf0")
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<ButtonPress-1>", self.on_header_press, add="+")
        self.tree.bind("<ButtonRelease-1>", self.on_header_release, add="+")

        page_bar = ttk.Frame(left_card)
        page_bar.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(page_bar, text="前へ", command=self.prev_page).pack(side="left")
        ttk.Label(page_bar, textvariable=self.page_var).pack(side="left", padx=8)
        ttk.Button(page_bar, text="次へ", command=self.next_page).pack(side="left")
        self.page_info_var = tk.StringVar(value="0 / 0")
        ttk.Label(page_bar, textvariable=self.page_info_var).pack(side="left", padx=12)

        ttk.Label(right_card, text="詳細", font=("Yu Gothic UI", 13, "bold")).pack(anchor="w")
        action_frame = ttk.Frame(right_card)
        action_frame.pack(fill="x", pady=(6, 8))
        ttk.Label(action_frame, text="選択中の処理:").pack(side="left")
        self.action_combo = ttk.Combobox(action_frame, textvariable=self.action_var, state="readonly", width=32,
                                         values=["選択側のファイルをゴミ箱へ移動", "選択側のファイルで更新", "何もしない"])
        self.action_combo.pack(side="left", padx=(6, 6))
        self.action_combo.bind("<<ComboboxSelected>>", self.on_action_selected)
        ttk.Button(action_frame, text="この項目を選択解除", command=self.clear_current_selection).pack(side="left")

        detail_frame = ttk.Frame(right_card)
        detail_frame.pack(fill="both", expand=False, pady=(0, 8))
        self.detail_info = tk.Text(detail_frame, height=14, wrap="word", font=("Yu Gothic UI", 10), state="disabled")
        detail_scroll_y = ttk.Scrollbar(detail_frame, orient="vertical", command=self.detail_info.yview)
        detail_scroll_x = ttk.Scrollbar(detail_frame, orient="horizontal", command=self.detail_info.xview)
        self.detail_info.configure(yscrollcommand=detail_scroll_y.set, xscrollcommand=detail_scroll_x.set)
        self.detail_info.grid(row=0, column=0, sticky="nsew")
        detail_scroll_y.grid(row=0, column=1, sticky="ns")
        detail_scroll_x.grid(row=1, column=0, sticky="ew")
        detail_frame.rowconfigure(0, weight=1)
        detail_frame.columnconfigure(0, weight=1)

        ttk.Label(right_card, text="本文・差分プレビュー", font=("Yu Gothic UI", 13, "bold")).pack(anchor="w")
        diff_frame = ttk.Frame(right_card)
        diff_frame.pack(fill="both", expand=True, pady=(6, 0))
        self.diff_text = tk.Text(diff_frame, height=18, wrap="none", font=("Consolas", 9), state="disabled")
        diff_scroll_y = ttk.Scrollbar(diff_frame, orient="vertical", command=self.diff_text.yview)
        diff_scroll_x = ttk.Scrollbar(diff_frame, orient="horizontal", command=self.diff_text.xview)
        self.diff_text.configure(yscrollcommand=diff_scroll_y.set, xscrollcommand=diff_scroll_x.set)
        self.diff_text.grid(row=0, column=0, sticky="nsew")
        diff_scroll_y.grid(row=0, column=1, sticky="ns")
        diff_scroll_x.grid(row=1, column=0, sticky="ew")
        diff_frame.rowconfigure(0, weight=1)
        diff_frame.columnconfigure(0, weight=1)

        log_card = ttk.Frame(self.outer, style="Card.TFrame", padding=10)
        log_card.pack(fill="both", expand=False, pady=(10, 0))
        ttk.Label(log_card, text="実行ログ", font=("Yu Gothic UI", 12, "bold")).pack(anchor="w")
        log_frame = ttk.Frame(log_card)
        log_frame.pack(fill="both", expand=True, pady=(6, 0))
        self.log_text = tk.Text(log_frame, height=10, wrap="none", font=("Consolas", 9), state="disabled")
        log_scroll_y = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll_x = ttk.Scrollbar(log_frame, orient="horizontal", command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=log_scroll_y.set, xscrollcommand=log_scroll_x.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll_y.grid(row=0, column=1, sticky="ns")
        log_scroll_x.grid(row=1, column=0, sticky="ew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        statusbar = ttk.Frame(self.outer)
        statusbar.pack(fill="x", pady=(8, 0))
        ttk.Label(statusbar, textvariable=self.statusbar_var).pack(side="left")

    def _apply_tree_columns(self) -> None:
        self.tree["displaycolumns"] = self.column_order
        self.tree["columns"] = self.column_order
        for col in self.column_order:
            self.tree.heading(col, text=self.COLUMN_LABELS[col], command=lambda c=col: self.sort_tree_by(c, False))
            self.tree.column(col, width=self.COLUMN_MIN_WIDTH.get(col, 100), anchor="w", stretch=True)
        self.column_picker["values"] = [self.COLUMN_LABELS[c] for c in self.column_order]
        if self.column_order:
            current = self.column_pick_var.get()
            if current not in self.column_picker["values"]:
                self.column_pick_var.set(self.COLUMN_LABELS[self.column_order[0]])

    def _path_row(self, parent, row, label, var, cmd):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 10))
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=6)
        ttk.Button(parent, text="参照", command=cmd).grid(row=row, column=2, sticky="w", padx=(10, 0), pady=6)
        parent.grid_columnconfigure(1, weight=1)

    def _simple_row(self, parent, row, label, var):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 10))
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, columnspan=2, sticky="ew", pady=6)
        parent.grid_columnconfigure(1, weight=1)

    def _set_readonly_text(self, widget: tk.Text, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

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

    def _progress_callback(self, current, total, message):
        total = max(total, 1)
        percent = int((current / total) * 100)
        self.root.after(0, lambda: self._apply_progress(percent, message, current, total))

    def _apply_progress(self, percent, message, current, total):
        self.progress["value"] = percent
        self.progress_label_var.set(f"{percent}%")
        self.status_var.set(message)
        if self.start_time is None:
            self.start_time = time.time()
        elapsed = max(time.time() - self.start_time, 0.001)
        rate = current / elapsed
        remain = max(total - current, 0)
        eta_seconds = int(remain / rate) if rate > 0 else 0
        eta_clock = time.strftime("%H:%M:%S", time.localtime(time.time() + eta_seconds))
        self.eta_var.set(f"終了予測: {eta_clock}")

    def log(self, message):
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{stamp}] {message}"
        self.log_lines.append(line)
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear_log(self):
        self.log_lines.clear()
        self._set_readonly_text(self.log_text, "")

    def clear_search(self):
        self.search_var.set("")
        self.page_var.set(1)
        self.refresh_tree()

    def _update_statusbar(self):
        target_count = sum(1 for x in self.scan_items if x.target_selected)
        compare_count = sum(1 for x in self.scan_items if x.compare_selected)
        planned_count = sum(1 for x in self.scan_items if (x.target_selected or x.compare_selected) and x.preferred_action != "何もしない")
        self.statusbar_var.set(f"対象側選択 {target_count}件 / 比較側選択 {compare_count}件 / 実行予定 {planned_count}件 / 最終スキャン {self.last_scan_time}")

    def _passes_filter(self, row: ScanItem):
        mode = self.filter_var.get()
        if mode == "同一ファイルのみ" and row.category != "同一ファイル":
            return False
        if mode == "更新候補のみ" and row.category != "更新候補":
            return False
        if mode == "同名・別内容のみ" and row.category != "同名・別内容":
            return False
        if mode == "サイズ差分候補のみ" and row.category != "サイズ差分候補":
            return False
        if mode == "選択中のみ" and not (row.target_selected or row.compare_selected):
            return False
        q = self.search_var.get().strip().lower()
        if q:
            merged = " ".join([row.category, row.confidence, row.preferred_action, row.reason, row.scope, row.target_path, row.compare_path, row.notes]).lower()
            if q not in merged:
                return False
        return True

    def _short_path(self, value, max_len=48):
        if len(value) <= max_len:
            return value
        return "..." + value[-(max_len - 3):]

    def _row_values(self, row: ScanItem):
        return {
            "target_selected": "☑" if row.target_selected else "☐",
            "compare_selected": "☑" if row.compare_selected else "☐",
            "category": row.category,
            "confidence": row.confidence,
            "action": row.preferred_action,
            "reason": row.reason,
            "scope": row.scope,
            "target": self._short_path(row.target_path),
            "compare": self._short_path(row.compare_path),
        }

    def _recompute_filtered_indices(self):
        self.filtered_indices = [idx for idx, row in enumerate(self.scan_items) if self._passes_filter(row)]
        total_pages = max((len(self.filtered_indices) - 1) // self.PAGE_SIZE + 1, 1)
        if self.page_var.get() > total_pages:
            self.page_var.set(total_pages)
        self.page_info_var.set(f"{self.page_var.get()} / {total_pages}")

    def refresh_tree(self):
        current_selection = self.tree.selection()
        self._recompute_filtered_indices()
        start = (self.page_var.get() - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        page_indices = self.filtered_indices[start:end]

        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for idx in page_indices:
            row = self.scan_items[idx]
            tag = "same"
            if row.category == "更新候補":
                tag = "update"
            elif row.category == "同名・別内容":
                tag = "name_diff"
            elif row.category == "サイズ差分候補":
                tag = "size_diff"
            values_map = self._row_values(row)
            self.tree.insert("", "end", iid=str(idx), values=[values_map[c] for c in self.column_order], tags=(tag,))

        restored = [iid for iid in current_selection if self.tree.exists(iid)]
        if restored:
            self.tree.selection_set(restored)
            self.tree.focus(restored[-1])
        elif self.tree.get_children():
            first = self.tree.get_children()[0]
            self.tree.selection_set((first,))
            self.tree.focus(first)

        self.auto_fit_columns(sample_only=True)
        self.on_tree_select()
        self._update_statusbar()

    def auto_fit_columns(self, sample_only=False):
        try:
            tv_font = tkfont.nametofont(str(self.tree.cget("font")))
        except Exception:
            tv_font = tkfont.nametofont("TkDefaultFont")

        max_rows = 80 if sample_only else len(self.tree.get_children())
        children = self.tree.get_children()[:max_rows]

        for col in self.column_order:
            label = self.COLUMN_LABELS[col]
            max_width = tv_font.measure(label) + 24
            for iid in children:
                value = str(self.tree.set(iid, col))
                max_width = max(max_width, tv_font.measure(value) + 24)
            max_width = min(max(max_width, self.COLUMN_MIN_WIDTH.get(col, 80)), 420)
            self.tree.column(col, width=max_width)

    def move_column_left(self):
        label = self.column_pick_var.get().strip()
        if not label:
            return
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
        if not label:
            return
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
        region = self.tree.identify("region", event.x, event.y)
        if region != "heading":
            self.drag_col = None
            return
        col_id = self.tree.identify_column(event.x)
        if not col_id:
            self.drag_col = None
            return
        display_cols = list(self.tree["displaycolumns"])
        disp_index = int(col_id.replace("#", "")) - 1
        if 0 <= disp_index < len(display_cols):
            self.drag_col = display_cols[disp_index]
        else:
            self.drag_col = None

    def on_header_release(self, event):
        if not self.drag_col:
            return
        region = self.tree.identify("region", event.x, event.y)
        if region != "heading":
            self.drag_col = None
            return
        col_id = self.tree.identify_column(event.x)
        if not col_id:
            self.drag_col = None
            return
        display_cols = list(self.tree["displaycolumns"])
        disp_index = int(col_id.replace("#", "")) - 1
        if not (0 <= disp_index < len(display_cols)):
            self.drag_col = None
            return
        target_col = display_cols[disp_index]
        if target_col != self.drag_col:
            old_idx = self.column_order.index(self.drag_col)
            new_idx = self.column_order.index(target_col)
            self.column_order.pop(old_idx)
            self.column_order.insert(new_idx, self.drag_col)
            self._apply_tree_columns()
            self.refresh_tree()
        self.drag_col = None

    def sort_tree_by(self, column, reverse):
        mapping = {
            "target_selected": lambda x: 1 if x.target_selected else 0,
            "compare_selected": lambda x: 1 if x.compare_selected else 0,
            "category": lambda x: x.category,
            "confidence": lambda x: {"低": 1, "中": 2, "高": 3}.get(x.confidence, 0),
            "action": lambda x: x.preferred_action,
            "reason": lambda x: x.reason,
            "scope": lambda x: x.scope,
            "target": lambda x: x.target_path,
            "compare": lambda x: x.compare_path,
        }
        self.scan_items.sort(key=mapping.get(column, lambda x: x.category), reverse=reverse)
        self.page_var.set(1)
        self.refresh_tree()
        self.tree.heading(column, command=lambda: self.sort_tree_by(column, not reverse))

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id:
            return
        index = int(item_id)
        display_cols = list(self.tree["displaycolumns"])
        disp_index = int(column.replace("#", "")) - 1
        if disp_index < 0 or disp_index >= len(display_cols):
            return
        logical_col = display_cols[disp_index]

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
        ids = [int(iid) for iid in self.tree.selection() if iid.isdigit()]
        self.current_detail_indices = ids
        self.show_detail(ids)

    def on_action_selected(self, _event=None):
        ids = self.current_detail_indices
        if not ids:
            return
        value = self.action_var.get().strip()
        if not value:
            return
        for idx in ids:
            if 0 <= idx < len(self.scan_items):
                self.scan_items[idx].preferred_action = value
        self.refresh_tree()
        keep = tuple(str(i) for i in ids if self.tree.exists(str(i)))
        if keep:
            self.tree.selection_set(keep)
        self.show_detail(ids)

    def show_detail(self, indices: list[int]):
        if not indices:
            self._set_readonly_text(self.detail_info, "")
            self._set_readonly_text(self.diff_text, "")
            self.action_var.set("何もしない")
            return

        valid = [i for i in indices if 0 <= i < len(self.scan_items)]
        if not valid:
            return

        if len(valid) == 1:
            item = self.scan_items[valid[0]]
            self.action_var.set(item.preferred_action)
            detail = [
                f"種類: {item.category}",
                f"信頼度: {item.confidence}",
                f"現在の処理: {item.preferred_action}",
                f"理由: {item.reason}",
                f"範囲: {item.scope}",
                f"選択状態: {item.selection_state_text()}",
                "",
                "対象フォルダ側ファイル:",
                f"  {item.target_path}",
                f"  サイズ: {item.target_size:,} byte",
                f"  更新日時: {datetime.fromtimestamp(item.target_mtime).strftime('%Y-%m-%d %H:%M:%S') if item.target_mtime else '-'}",
                "",
                "比較フォルダ側ファイル:",
                f"  {item.compare_path}",
                f"  サイズ: {item.compare_size:,} byte",
                f"  更新日時: {datetime.fromtimestamp(item.compare_mtime).strftime('%Y-%m-%d %H:%M:%S') if item.compare_mtime else '-'}",
                "",
                f"本文の近さ: {item.similarity * 100:.1f}%",
                f"差分要約: {item.diff_summary}",
                f"補足: {item.notes}",
            ]
            self._set_readonly_text(self.detail_info, "\n".join(detail))

            target_preview = read_text_preview(item.target_path, max_chars=1800)
            compare_preview = read_text_preview(item.compare_path, max_chars=1800)
            diff_lines = list(difflib.unified_diff(
                target_preview.splitlines(), compare_preview.splitlines(),
                fromfile="対象フォルダ側", tofile="比較フォルダ側", lineterm=""
            ))
            if not diff_lines:
                diff_text = "差分が見つからないか、本文比較対象外です。\n\n"
            else:
                diff_text = "\n".join(diff_lines[:300]) + "\n\n"
            diff_text += "---- 対象フォルダ側プレビュー ----\n" + target_preview[:2000] + "\n\n"
            diff_text += "---- 比較フォルダ側プレビュー ----\n" + compare_preview[:2000]
            self._set_readonly_text(self.diff_text, diff_text)
            return

        selected_items = [self.scan_items[i] for i in valid]
        target_count = sum(1 for x in selected_items if x.target_selected)
        compare_count = sum(1 for x in selected_items if x.compare_selected)
        categories = {}
        actions = {}
        for item in selected_items:
            categories[item.category] = categories.get(item.category, 0) + 1
            actions[item.preferred_action] = actions.get(item.preferred_action, 0) + 1

        if len(actions) == 1:
            self.action_var.set(next(iter(actions.keys())))
        else:
            self.action_var.set("何もしない")

        lines = [
            f"複数選択: {len(selected_items)}件",
            f"対象側チェック: {target_count}件",
            f"比較側チェック: {compare_count}件",
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
        self._set_readonly_text(self.detail_info, "\n".join(lines))

        preview_lines = ["複数選択中のため、本文差分は個別表示ではなく一覧要約を表示しています。", ""]
        for idx, item in enumerate(selected_items[:20], start=1):
            side = item.selection_state_text()
            preview_lines.append(f"[{idx}] {item.category} / {side} / {item.reason}")
            preview_lines.append(f"    対象: {item.target_path}")
            preview_lines.append(f"    比較: {item.compare_path}")
        if len(selected_items) > 20:
            preview_lines.append("")
            preview_lines.append(f"…他 {len(selected_items) - 20} 件")
        self._set_readonly_text(self.diff_text, "\n".join(preview_lines))

    def clear_current_selection(self):
        ids = self.current_detail_indices
        if not ids:
            return
        for idx in ids:
            item = self.scan_items[idx]
            item.target_selected = False
            item.compare_selected = False
        self.refresh_tree()

    def select_all_target(self):
        for row in self.scan_items:
            if self._passes_filter(row):
                row.target_selected = True
                row.compare_selected = False
        self.refresh_tree()

    def select_all_compare(self):
        for row in self.scan_items:
            if self._passes_filter(row):
                row.compare_selected = True
                row.target_selected = False
        self.refresh_tree()

    def clear_all_selection(self):
        for row in self.scan_items:
            row.target_selected = False
            row.compare_selected = False
        self.refresh_tree()

    def select_smaller_side(self):
        target_files = len([x for x in self.scan_items if x.target_path])
        compare_files = len([x for x in self.scan_items if x.compare_path])
        if target_files <= compare_files:
            self.select_all_target()
        else:
            self.select_all_compare()

    def select_larger_side(self):
        target_files = len([x for x in self.scan_items if x.target_path])
        compare_files = len([x for x in self.scan_items if x.compare_path])
        if target_files > compare_files:
            self.select_all_target()
        else:
            self.select_all_compare()

    def prev_page(self):
        if self.page_var.get() > 1:
            self.page_var.set(self.page_var.get() - 1)
            self.refresh_tree()

    def next_page(self):
        total_pages = max((len(self.filtered_indices) - 1) // self.PAGE_SIZE + 1, 1)
        if self.page_var.get() < total_pages:
            self.page_var.set(self.page_var.get() + 1)
            self.refresh_tree()

    def _set_scanning_state(self, is_scanning: bool):
        self.is_scanning = is_scanning
        state = "disabled" if is_scanning else "normal"
        self.scan_btn.configure(state=state)
        self.preview_btn.configure(state=state)
        self.exec_btn.configure(state=state)

    def scan(self):
        if self.is_scanning:
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

        self.start_time = time.time()
        self.progress["value"] = 0
        self.progress_label_var.set("0%")
        self.eta_var.set("終了予測: 計算中")
        self.status_var.set("スキャンを開始します")
        self.log("スキャン開始")
        self._set_scanning_state(True)

        def worker():
            try:
                items, summary = scan_folders(
                    source_dir=source,
                    compare_dir=compare or None,
                    exclude_dirs=self._exclude_dirs(),
                    exclude_exts=self._exclude_exts(),
                    progress_cb=self._progress_callback,
                )
                self.root.after(0, lambda: self._scan_finished(items, summary))
            except Exception as e:
                self.root.after(0, lambda: self._scan_failed(e))

        threading.Thread(target=worker, daemon=True).start()

    def _scan_finished(self, items, summary):
        self.scan_items = items
        self.last_scan_time = datetime.now().strftime("%H:%M:%S")
        self.summary_var.set(
            f"対象フォルダ {summary['source_files']}件 / 比較フォルダ {summary['compare_files']}件 / "
            f"同一 {summary['same_items']}件 / 更新候補 {summary['update_items']}件 / "
            f"同名別内容 {summary['same_name_diff_items']}件 / サイズ差分 {summary['size_diff_items']}件"
        )
        self.status_var.set("スキャンが完了しました")
        self.progress["value"] = 100
        self.progress_label_var.set("100%")
        self.page_var.set(1)
        self.refresh_tree()
        self.log(f"スキャン完了: 候補 {summary['total_items']}件")
        self._set_scanning_state(False)
        if not self.scan_items:
            messagebox.showinfo("結果", "該当する候補は見つかりませんでした。")

    def _scan_failed(self, error):
        self.log(f"スキャン失敗: {error}")
        self._set_scanning_state(False)
        messagebox.showerror("エラー", f"スキャン中に問題が発生しました。\n{error}")

    def preview_changes(self):
        selected = [x for x in self.scan_items if (x.target_selected or x.compare_selected) and x.preferred_action != "何もしない"]
        if not selected:
            messagebox.showinfo("確認", "現在、実行対象に選ばれている項目はありません。")
            return
        counts = {}
        for x in selected:
            side = "対象側" if x.target_selected else "比較側"
            label = f"{side}: {x.preferred_action}"
            counts[label] = counts.get(label, 0) + 1

        lines = ["この確認では、まだ実際の変更は行いません。", "", f"選択中の件数: {len(selected)}件", "", "実行予定の処理:"]
        for k, v in counts.items():
            lines.append(f"  ・{k}: {v}件")
        lines += ["", "ゴミ箱移動や更新は実行時に警告が出ます。"]
        messagebox.showinfo("変更内容の確認", "\n".join(lines))

    def _confirm_dangerous_actions(self, selected):
        trash_count = sum(1 for x in selected if x.preferred_action == "選択側のファイルをゴミ箱へ移動")
        update_count = sum(1 for x in selected if x.preferred_action == "選択側のファイルで更新")
        if trash_count:
            if not messagebox.askyesno("警告: ゴミ箱移動を含みます", f"ゴミ箱移動を含む処理が {trash_count} 件あります。\n続行しますか？"):
                return False
        if update_count:
            if not messagebox.askyesno("警告: 上書き更新を含みます", f"上書き更新を含む処理が {update_count} 件あります。\n現在の内容は置き換わります。\n本当に続行しますか？"):
                return False
        return True

    def execute(self):
        selected = [x for x in self.scan_items if (x.target_selected or x.compare_selected) and x.preferred_action != "何もしない"]
        if not selected:
            messagebox.showwarning("未選択", "実行対象がありません。")
            return
        counts = {}
        for x in selected:
            side = "対象側" if x.target_selected else "比較側"
            label = f"{side}: {x.preferred_action}"
            counts[label] = counts.get(label, 0) + 1
        msg_lines = ["次の内容を実行します。", ""]
        for k, v in counts.items():
            msg_lines.append(f"・{k}: {v}件")
        msg_lines += ["", "実行しますか？"]
        if not messagebox.askyesno("最終確認", "\n".join(msg_lines)):
            return
        if not self._confirm_dangerous_actions(selected):
            return
        try:
            results = execute_items(selected)
            summary = {
                "実行対象件数": len(selected),
                "成功件数": sum(1 for r in results if r["status"] == "成功"),
                "失敗件数": sum(1 for r in results if r["status"] != "成功"),
                "対象フォルダ": self.source_var.get().strip(),
                "比較フォルダ": self.compare_var.get().strip(),
            }
            report_path = self.report_manager.save_report(summary, results)
            success = summary["成功件数"]
            fail = summary["失敗件数"]
            self.status_var.set("処理が完了しました")
            self.log(f"実行完了: 成功 {success}件 / 失敗 {fail}件")
            self.log(f"レポート保存: {report_path}")
            for r in results:
                if r["status"] == "成功":
                    self.log(f"成功: {r['action']} / {r['target']} / {r.get('message', '')}")
                else:
                    self.log(f"失敗: {r['target']} / {r.get('error', '不明なエラー')}")
            messagebox.showinfo("完了", f"処理が完了しました。\n成功: {success}件\n失敗: {fail}件\n\nレポート:\n{report_path}")
            self.scan()
        except Exception as e:
            self.log(f"実行失敗: {e}")
            messagebox.showerror("エラー", f"実行中に問題が発生しました。\n{e}")

    def on_close(self):
        try:
            payload = {
                "last_source_dir": self.source_var.get().strip(),
                "last_compare_dir": self.compare_var.get().strip(),
                "window_geometry": self.root.geometry(),
                "filter_mode": self.filter_var.get(),
                "search_text": self.search_var.get(),
                "exclude_dirs": self._exclude_dirs(),
                "exclude_exts": self._exclude_exts(),
                "column_order": self.column_order,
            }
            self.settings_manager.save(payload)
        except Exception:
            pass
        self.root.destroy()

    def save_settings(self):
        try:
            payload = {
                "last_source_dir": self.source_var.get().strip(),
                "last_compare_dir": self.compare_var.get().strip(),
                "window_geometry": self.root.geometry(),
                "filter_mode": self.filter_var.get(),
                "search_text": self.search_var.get(),
                "exclude_dirs": self._exclude_dirs(),
                "exclude_exts": self._exclude_exts(),
                "column_order": self.column_order,
            }
            self.settings_manager.save(payload)
            self.log("設定を保存しました")
            messagebox.showinfo("保存", "設定を保存しました。")
        except Exception as e:
            self.log(f"設定保存失敗: {e}")
            messagebox.showerror("エラー", f"設定保存に失敗しました。\n{e}")

    def run(self):
        self.root.mainloop()
