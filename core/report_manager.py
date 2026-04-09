from __future__ import annotations

import csv
from datetime import datetime
import html
import json
from pathlib import Path
from typing import Any, Iterable


class ReportManager:
    def __init__(self, base_dir: str) -> None:
        self.report_dir = Path(base_dir) / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.last_saved_bundle: dict[str, str] = {}

    def _normalize_rows(self, rows: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for row in rows or []:
            if isinstance(row, dict):
                normalized.append(dict(row))
        return normalized

    def _build_base_path(self, prefix: str) -> Path:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return self.report_dir / f"{stamp}_{prefix}"

    def _write_txt(self, path: Path, title: str, summary: dict[str, Any], rows: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
        lines = [title, "=" * 72, f"作成日時: {datetime.now():%Y-%m-%d %H:%M:%S}", ""]
        if metadata:
            lines += ["メタ情報", "-" * 72]
            for key, value in metadata.items():
                lines.append(f"{key}: {value}")
            lines.append("")
        if summary:
            lines += ["サマリー", "-" * 72]
            for key, value in summary.items():
                lines.append(f"{key}: {value}")
            lines.append("")
        lines += ["詳細", "-" * 72]
        for idx, row in enumerate(rows, start=1):
            lines.append(f"[{idx}]")
            for key, value in row.items():
                lines.append(f" {key}: {value}")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    def _write_json(self, path: Path, title: str, summary: dict[str, Any], rows: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
        payload = {
            "title": title,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary,
            "metadata": metadata,
            "rows": rows,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        fieldnames: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames or ["message"])
            writer.writeheader()
            if rows:
                writer.writerows(rows)
            else:
                writer.writerow({"message": "データなし"})

    def _write_html(self, path: Path, title: str, summary: dict[str, Any], rows: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
        columns: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    columns.append(key)
        header = "".join(f"<th>{html.escape(col)}</th>" for col in columns)
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(row.get(col, '')))}</td>" for col in columns) + "</tr>"
            for row in rows
        )
        summary_html = "".join(
            f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
            for key, value in summary.items()
        )
        metadata_html = "".join(
            f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
            for key, value in metadata.items()
        )
        html_text = f"""<!doctype html>
<html lang=\"ja\">
<head>
  <meta charset=\"utf-8\">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: sans-serif; margin: 24px; color: #223; }}
    h1, h2 {{ margin-bottom: 8px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #cfd6df; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f2f5f8; width: 24%; }}
    .meta th {{ width: 24%; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p>作成日時: {datetime.now():%Y-%m-%d %H:%M:%S}</p>
  <h2>メタ情報</h2>
  <table class=\"meta\">{metadata_html or '<tr><td colspan="2">なし</td></tr>'}</table>
  <h2>サマリー</h2>
  <table class=\"meta\">{summary_html or '<tr><td colspan="2">なし</td></tr>'}</table>
  <h2>詳細</h2>
  <table>
    <thead><tr>{header}</tr></thead>
    <tbody>{body or '<tr><td colspan="99">データなし</td></tr>'}</tbody>
  </table>
</body>
</html>
"""
        path.write_text(html_text, encoding="utf-8")

    def save_bundle(
        self,
        *,
        title: str,
        prefix: str,
        summary: dict[str, Any] | None,
        rows: Iterable[dict[str, Any]] | None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        summary = dict(summary or {})
        metadata = dict(metadata or {})
        normalized_rows = self._normalize_rows(rows)
        base = self._build_base_path(prefix)
        paths = {
            "txt": str(base.with_suffix(".txt")),
            "json": str(base.with_suffix(".json")),
            "csv": str(base.with_suffix(".csv")),
            "html": str(base.with_suffix(".html")),
        }
        self._write_txt(Path(paths["txt"]), title, summary, normalized_rows, metadata)
        self._write_json(Path(paths["json"]), title, summary, normalized_rows, metadata)
        self._write_csv(Path(paths["csv"]), normalized_rows)
        self._write_html(Path(paths["html"]), title, summary, normalized_rows, metadata)
        self.last_saved_bundle = paths
        return paths

    def save_report(self, summary: dict, results: list[dict]) -> str:
        bundle = self.save_bundle(
            title="ファイル管理ツール 実行レポート",
            prefix="実行結果",
            summary=summary,
            rows=results,
        )
        return bundle["txt"]

    def save_preview_report(self, summary: dict, rows: list[dict]) -> dict[str, str]:
        return self.save_bundle(
            title="ファイル管理ツール 変更予定レポート",
            prefix="変更予定",
            summary=summary,
            rows=rows,
        )

    def save_history_report(self, session_details: dict) -> dict[str, str]:
        summary = {
            "stamp": session_details.get("stamp", ""),
            "created_at": session_details.get("created_at", ""),
            "entry_count": session_details.get("entry_count", 0),
            "operations": session_details.get("operations", {}),
        }
        return self.save_bundle(
            title="ファイル管理ツール 履歴レポート",
            prefix="履歴詳細",
            summary=summary,
            rows=session_details.get("entries", []),
            metadata=session_details.get("metadata", {}),
        )
