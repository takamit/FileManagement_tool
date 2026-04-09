# FileManagement Tool

## 概要
Python製のGUIファイル管理ツールです。  
2つのフォルダ（対象 / 比較）を比較し、不要ファイルの削除・更新・整理を安全かつ効率的に行うことを目的としています。

## ディレクトリ構成
```text
FileManagement_tool/
├─ ui/                  # 画面・表示・イベント受付
│  ├─ __init__.py
│  └─ gui.py
├─ core/                # 内部ロジック
│  ├─ __init__.py
│  ├─ backup_manager.py
│  ├─ classifier.py
│  ├─ compare_detector.py
│  ├─ config_manager.py
│  ├─ content_tools.py
│  ├─ duplicate_detector.py
│  ├─ executor.py
│  ├─ filename_analyzer.py
│  ├─ hasher.py
│  ├─ history_manager.py
│  ├─ logger_service.py
│  ├─ log_manager.py
│  ├─ progress_service.py
│  ├─ report.py
│  ├─ report_manager.py
│  ├─ runtime_control.py
│  ├─ scanner.py
│  ├─ series_detector.py
│  ├─ settings_manager.py
│  ├─ utils.py
│  └─ version_detector.py
├─ models/
│  ├─ __init__.py
│  ├─ file_record.py
│  └─ result_models.py
├─ config/
│  └─ classify_rules.json
├─ docs/
│  ├─ spec.md
│  └─ refactor_plan.md
├─ main.py
├─ requirements.txt
├─ README.md
└─ .gitignore
```

## セットアップ
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

## 実行
```powershell
python main.py
```

## 方針
- UI は `ui/` に統一
- 内部ロジックは `core/` に統一
- 既存機能は可能な限り維持しつつ、生成物とローカル状態ファイルは除外
