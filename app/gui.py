import tkinter as tk
from tkinter import ttk, messagebox


def run_app() -> None:
    root = tk.Tk()
    root.title("FileManagement Tool")
    root.geometry("900x600")

    header = ttk.Frame(root, padding=12)
    header.pack(fill="x")

    ttk.Label(header, text="FileManagement Tool").pack(anchor="w")
    ttk.Label(header, text="構造整理版の起動確認用 GUI").pack(anchor="w", pady=(4, 0))

    body = ttk.Frame(root, padding=12)
    body.pack(fill="both", expand=True)

    tree = ttk.Treeview(body, columns=("category", "target", "compare"), show="headings")
    tree.heading("category", text="分類")
    tree.heading("target", text="対象")
    tree.heading("compare", text="比較")
    tree.pack(fill="both", expand=True)

    footer = ttk.Frame(root, padding=12)
    footer.pack(fill="x")

    def on_about() -> None:
        messagebox.showinfo(
            "Info",
            "このGUIは、既存プロジェクトを整理するための基準構造です。"
        )

    ttk.Button(footer, text="Info", command=on_about).pack(side="right")
    root.mainloop()
