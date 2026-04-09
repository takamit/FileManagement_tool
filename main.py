from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from core.backup_manager import BackupManager
from core.logic.cli_controller import CliController, CliScanRequest
from core.report_manager import ReportManager
from core.settings_manager import SettingsManager
from ui.gui import FileManagerApp

try:
    from ui.gui_enhancements import apply_gui_enhancements
except Exception:
    apply_gui_enhancements = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ファイル管理ツール")
    parser.add_argument("--mode", choices=["gui", "cli"], default="gui", help="起動モード")
    parser.add_argument("--source", default="", help="対象フォルダ")
    parser.add_argument("--compare", default="", help="比較フォルダ")
    parser.add_argument("--exclude-dirs", default="", help="除外フォルダをカンマ区切りで指定")
    parser.add_argument("--exclude-exts", default="", help="除外拡張子をカンマ区切りで指定")
    parser.add_argument(
        "--action",
        choices=["scan", "preview", "export-preview", "apply", "undo-last", "list-history", "export-history"],
        default="scan",
    )
    parser.add_argument("--dry-run", action="store_true", help="変更を適用せず、実行予定のみを出力")
    parser.add_argument("--report", default="", help="レポート出力先パス")
    parser.add_argument("--report-format", choices=["json", "csv", "html", "txt"], default="")
    parser.add_argument("--base-dir", default=".", help="設定・バックアップ保存の基準ディレクトリ")
    parser.add_argument("--undo-manifest", default="", help="undo / 履歴対象の manifest.json パス")
    return parser


def _build_request(args: argparse.Namespace) -> CliScanRequest:
    return CliScanRequest(
        source_dir=args.source,
        compare_dir=args.compare,
        exclude_dirs=[x.strip() for x in args.exclude_dirs.split(",") if x.strip()],
        exclude_exts=[x.strip() for x in args.exclude_exts.split(",") if x.strip()],
    )


def run_cli(args: argparse.Namespace) -> int:
    base_dir = Path(args.base_dir)
    settings = SettingsManager(str(base_dir)).load()
    controller = CliController()
    backup_manager = BackupManager(str(base_dir), max_sessions=settings["history_limit"])
    report_manager = ReportManager(str(base_dir))

    if args.action == "list-history":
        print(json.dumps({"history": backup_manager.list_recent_sessions(limit=None)}, ensure_ascii=False, indent=2))
        return 0

    if args.action in {"undo-last", "export-history"}:
        manifest_path = args.undo_manifest
        if not manifest_path:
            recent = backup_manager.list_recent_sessions(limit=1)
            if not recent:
                print("戻せる履歴がありません。", file=sys.stderr)
                return 1
            manifest_path = recent[0]["manifest_path"]
        if args.action == "undo-last":
            success, failed, messages = backup_manager.undo_session(manifest_path)
            print(json.dumps({"success": success, "failed": failed, "messages": messages}, ensure_ascii=False, indent=2))
            return 0 if failed == 0 else 1
        bundle = report_manager.save_history_report(backup_manager.describe_session(manifest_path))
        print(json.dumps({"report_paths": bundle}, ensure_ascii=False, indent=2))
        return 0

    if not args.source:
        print("CLIモードでは --source が必須です。", file=sys.stderr)
        return 2

    request = _build_request(args)

    if args.action == "scan":
        items, summary = controller.scan(request)
        payload = {"items": len(items), "summary": summary}
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0

    if args.action == "preview":
        rows = controller.preview(request)
        print(json.dumps({"items": rows}, ensure_ascii=False, indent=2, default=str))
        return 0

    if args.action == "export-preview":
        report_path = args.report
        if not report_path:
            report_dir = base_dir / settings["report_output_dir"]
            report_dir.mkdir(parents=True, exist_ok=True)
            report_path = str(report_dir / f"preview_report.{args.report_format or settings['report_format']}")
        exported = controller.export_preview(request, report_path, format_hint=args.report_format or settings["report_format"])
        print(json.dumps({"report_path": exported}, ensure_ascii=False, indent=2))
        return 0

    if args.action == "apply":
        results, manifest_path = controller.apply(request, base_dir=str(base_dir), dry_run=args.dry_run)
        payload = {"results": results, "manifest_path": manifest_path, "dry_run": args.dry_run}
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0

    print(f"未対応の action です: {args.action}", file=sys.stderr)
    return 2


def run_gui() -> int:
    if callable(apply_gui_enhancements):
        apply_gui_enhancements(FileManagerApp)
    FileManagerApp().run()
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.mode == "cli":
        return run_cli(args)
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
