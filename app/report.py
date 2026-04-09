from __future__ import annotations

from datetime import datetime
from pathlib import Path

from models.result_models import ScanResults


class ReportWriter:
    def __init__(self, report_dir: Path) -> None:
        self.report_dir = report_dir
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def write_scan_report(self, results: ScanResults) -> Path:
        report_path = self.report_dir / f"scan_report_{datetime.now():%Y%m%d_%H%M%S}.txt"
        lines: list[str] = []
        lines.append("=== ファイル管理ツール スキャン結果 ===")
        lines.append(f"総ファイル数(精査元): {len(results.files)}")
        lines.append(f"対象内 重複グループ数: {len(results.duplicate_groups)}")
        lines.append(f"対象内 更新版候補数: {len(results.update_candidates)}")
        lines.append(f"対象内 シリーズ候補数: {len(results.series_groups)}")
        lines.append(f"比較 重複グループ数: {len(results.compare_duplicate_groups)}")
        lines.append(f"比較 更新版候補数: {len(results.compare_update_candidates)}")
        lines.append("")
        for group in results.duplicate_groups:
            lines.append(f"[対象内重複] {group.sha256}")
            for file in group.files:
                lines.append(f"  - {file.path}")
        lines.append("")
        for candidate in results.update_candidates:
            lines.append(
                f"[対象内更新版候補] old={candidate.old_file.path} | new={candidate.new_file.path} | 理由={candidate.reason}"
            )
        lines.append("")
        for series in results.series_groups:
            lines.append(f"[シリーズ候補] {series.key}")
            for file in series.files:
                lines.append(f"  - {file.path}")
        lines.append("")
        for group in results.compare_duplicate_groups:
            lines.append(f"[比較重複] {group.sha256}")
            for file in group.files:
                lines.append(f"  - {file.path}")
        lines.append("")
        for candidate in results.compare_update_candidates:
            lines.append(
                f"[比較更新候補] source={candidate.old_file.path} | reference={candidate.new_file.path} | 理由={candidate.reason}"
            )
        lines.append("")
        for error in results.errors:
            lines.append(f"[ERROR] {error}")
        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path
