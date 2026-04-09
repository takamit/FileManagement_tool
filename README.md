# FileManagement Tool

既存の `takamit/FileManagement_tool` を流用しつつ、開発標準設定に合わせて再配置・補強した版です。
ローカルへそのまま配置し、`.venv` を作成して依存関係を入れれば、開発と実行を始められる状態にしてあります。

## 設計方針

- Python 3.12 系を前提
- 仮想環境は `.venv` に統一
- `main.py` は CLI / GUI の起動分岐のみ
- UI とロジックを分離
- `core/logic`, `core/services`, `core/utils`, `core/models` の責務を固定
- 例外は握り潰さず、ログへ記録する

## ディレクトリ構成

```text
FileManagement_tool/
├─ main.py
├─ requirements.txt
├─ README.md
├─ .gitignore
├─ config/
│  ├─ __init__.py
│  ├─ app_config.py
│  ├─ logging_config.py
│  └─ classify_rules.json
├─ core/
│  ├─ __init__.py
│  ├─ logic/
│  │  ├─ __init__.py
│  │  ├─ classifier.py
│  │  ├─ cli_controller.py
│  │  ├─ compare_detector.py
│  │  ├─ duplicate_detector.py
│  │  ├─ file_management_logic.py
│  │  ├─ file_manager_logic.py
│  │  ├─ filename_analyzer.py
│  │  ├─ series_detector.py
│  │  └─ version_detector.py
│  ├─ services/
│  │  ├─ __init__.py
│  │  ├─ backup_manager.py
│  │  ├─ backup_service.py
│  │  ├─ content_tools.py
│  │  ├─ executor.py
│  │  ├─ file_operation_service.py
│  │  ├─ file_scanner_service.py
│  │  ├─ history_manager.py
│  │  ├─ report.py
│  │  ├─ report_manager.py
│  │  ├─ scanner.py
│  │  └─ settings_manager.py
│  ├─ utils/
│  │  ├─ __init__.py
│  │  ├─ formatters.py
│  │  ├─ hasher.py
│  │  ├─ log_manager.py
│  │  ├─ logger.py
│  │  ├─ logger_service.py
│  │  ├─ path_validator.py
│  │  ├─ progress_service.py
│  │  └─ runtime_control.py
│  └─ models/
│     ├─ __init__.py
│     ├─ file_record.py
│     └─ result_models.py
├─ ui/
│  ├─ __init__.py
│  ├─ gui.py
│  └─ components/
│     ├─ __init__.py
│     ├─ .gitkeep
│     └─ README.md
├─ tests/
│  ├─ __init__.py
│  ├─ test_imports.py
│  ├─ test_main_cli.py
│  └─ test_spec_structure.py
├─ docs/
│  ├─ __init__.py
│  ├─ legacy_refactor_plan.md
│  ├─ legacy_spec.md
│  ├─ local_setup.md
│  ├─ migration_notes.md
│  └─ specification_alignment.md
├─ logs/
│  └─ .gitkeep
└─ data/
   ├─ .gitkeep
   └─ temp/
      └─ .gitkeep
```

## セットアップ

### 1. 仮想環境を作成

```powershell
python -m venv .venv
```

### 2. 仮想環境を有効化

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. 依存関係をインストール

```powershell
pip install -r requirements.txt
```

## 起動方法

### GUI モード

```powershell
python main.py --mode gui
```

### CLI モード

```powershell
python main.py --mode cli --source "C:/target" --compare "C:/compare"
```

オプション例:

```powershell
python main.py --mode cli --source "C:/target" --compare "C:/compare" --exclude-dirs ".git,node_modules" --exclude-exts ".tmp,.log"
```

## テスト

```powershell
pytest
```

## GitHub 運用

- 安定版: `main`
- 機能追加: `feature/*`
- バグ修正: `fix/*`
- 依存更新時は `requirements.txt` を更新
- 構成変更時は `README.md` と `docs/` を更新

## GitHub 既存リポジトリへの反映

既存の `takamit/FileManagement_tool` ローカル環境へ上書き反映する場合は、`docs/github_overwrite_guide.md` を参照してください。

## 補足

- `core/logic/file_management_logic.py` は設計書向けの統一入口です。
- 既存実装の互換性維持のため、`core/logic/file_manager_logic.py` も残しています。
- `core/services/*_service.py` と `core/utils/logger.py` などの追加ファイルは、責務の見通しを良くするための整備用ラッパーです。


## PowerShell 手順

Windows ローカル環境で既存リポジトリへ上書き反映する場合は、`docs/powershell_local_overwrite_guide.md` を参照してください。
