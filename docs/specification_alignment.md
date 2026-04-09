# 設計適合メモ

この文書は、既存の `takamit/FileManagement_tool` を、Python 開発標準設定へどのように合わせたかを整理したものです。

## 1. 開発前提

反映内容:

- Python 3.12 系前提の記載を README に明記
- 仮想環境を `.venv` に統一
- GitHub 前提のブランチ運用を README に明記
- `requirements.txt` を同梱し、再現可能なセットアップ手順を記載

## 2. ディレクトリ構成

反映内容:

- `config/`, `core/`, `ui/`, `tests/`, `docs/`, `logs/`, `data/` を配置
- `core/` 配下を `logic / services / utils / models` に固定
- `ui/components/` を配置
- 空ディレクトリは `.gitkeep` を配置して維持
- `models/` のトップレベル配置は廃止し、`core/models/` に統一

## 3. レイヤー責務

### main.py
- CLI / GUI の起動分岐のみ
- 実処理は `core/logic/cli_controller.py` または `ui/gui.py` に委譲

### ui/
- 画面表示、入力受付、結果表示のみ
- ファイル走査や実行処理は `core/logic` 経由で呼び出す

### core/logic/
- 入力値の整理
- スキャンや実行の制御
- サービス層の呼び出し

### core/services/
- 走査、実行、バックアップ、設定、レポートなどの I/O 処理

### core/utils/
- ログ、パス検証、進捗、ハッシュ、表示補助

### core/models/
- データ構造の定義

## 4. 実行構造

反映内容:

- 単一入口を `main.py` に統一
- `--mode gui` と `--mode cli` を選択可能
- CLI / GUI の両方が同じサービス群を利用する構成

## 5. 命名規則

反映内容:

- 追加ファイルは snake_case で統一
- クラス名は PascalCase
- 変数・関数は snake_case
- 定数は UPPER_SNAKE_CASE

なお、既存資産由来のファイル名は極力維持しつつ、新設ファイルは規約に合わせています。

## 6. 実装ルール

反映内容:

- 1 関数 1 責務を意識してラッパー層を追加
- ログ関連ユーティリティを追加
- パス検証ユーティリティを追加
- マジックナンバー的な設定値は `config/` 側へ集約しやすい形へ補強
- 型ヒントを維持または追加

## 7. エラー処理

反映内容:

- 無言失敗を避ける方針を README / docs に反映
- 例外処理は既存コードを維持しつつ、ログ出力の置き場を `logs/` に統一

## 8. GitHub 運用

反映内容:

- `main`, `feature/*`, `fix/*` の運用を README に記載
- `.gitignore` を整理
- 共有前に README と docs を更新する前提を明記

## 9. .gitignore

反映内容:

- `.venv/`
- `__pycache__/`
- `*.pyc`
- `*.log`
- `.env`
- `.vscode/`
- `.idea/`
- `data/temp/`

加えて、実運用で発生する `.pytest_cache/`, `.coverage`, `htmlcov/`, `backup/`, `reports/`, `history/`, `config/settings.json` も除外しています。

## 10. テスト方針

反映内容:

- import 確認
- CLI 起動確認
- 設計書で要求した構成の存在確認

## 11. まだ残る整理余地

- 既存 GUI は大型の単一ファイル寄りなので、今後 `ui/components/` への分割余地あり
- 既存ロジックは互換性優先で残しているため、将来的に `file_management_logic.py` へさらに入口を寄せられる
- 既存サービス名と設計書向けラッパー名が併存しているため、段階的統合は今後の課題
