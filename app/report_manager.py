from __future__ import annotations
from pathlib import Path
from datetime import datetime

class ReportManager:
    def __init__(self, base_dir: str) -> None:
        self.report_dir = Path(base_dir) / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def save_report(self, summary: dict, results: list[dict]) -> str:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = self.report_dir / f"{stamp}_実行結果.txt"
        lines = ["ファイル管理ツール 実行レポート", "=" * 72, f"作成日時: {datetime.now():%Y-%m-%d %H:%M:%S}", "", "サマリー", "-" * 72]
        for k, v in summary.items():
            lines.append(f"{k}: {v}")
        lines += ["", "詳細", "-" * 72]
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] 状態: {r.get('status','')}")
            lines.append(f"    分類: {r.get('kind','')}")
            lines.append(f"    処理: {r.get('action','')}")
            lines.append(f"    対象: {r.get('target','')}")
            if r.get("source_used"):
                lines.append(f"    更新元: {r['source_used']}")
            if r.get("backup_path"):
                lines.append(f"    バックアップ: {r['backup_path']}")
            if r.get("message"):
                lines.append(f"    補足: {r['message']}")
            if r.get("error"):
                lines.append(f"    エラー: {r['error']}")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        return str(path)
