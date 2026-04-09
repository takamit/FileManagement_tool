from __future__ import annotations

import argparse
import json
import sys

from core.logic.cli_controller import CliController, CliScanRequest
from ui.gui import FileManagerApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ファイル管理ツール")
    parser.add_argument("--mode", choices=["gui", "cli"], default="gui", help="起動モード")
    parser.add_argument("--source", default="", help="対象フォルダ")
    parser.add_argument("--compare", default="", help="比較フォルダ")
    parser.add_argument("--exclude-dirs", default="", help="除外フォルダをカンマ区切りで指定")
    parser.add_argument("--exclude-exts", default="", help="除外拡張子をカンマ区切りで指定")
    return parser


def run_cli(args: argparse.Namespace) -> int:
    if not args.source:
        print("CLIモードでは --source が必須です。", file=sys.stderr)
        return 2

    controller = CliController()
    request = CliScanRequest(
        source_dir=args.source,
        compare_dir=args.compare,
        exclude_dirs=[x.strip() for x in args.exclude_dirs.split(',') if x.strip()],
        exclude_exts=[x.strip() for x in args.exclude_exts.split(',') if x.strip()],
    )
    items, summary = controller.scan(request)
    payload = {
        "items": len(items),
        "summary": summary,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


def run_gui() -> int:
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
