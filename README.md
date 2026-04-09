# FileManagement Tool

## 概要
2つのフォルダを比較し、差分検出・削除・更新・整理を行う Python 製 GUI ツールです。

## 目的
- フォルダ差分の把握
- 不要ファイル削除の効率化
- move ベースの安全な更新
- バックアップ / Undo による保全

## 現在の推奨構成
```text
FileManagement_tool/
├─ app/
│  ├─ gui.py
│  ├─ scanner.py
│  ├─ executor.py
│  └─ services.py
├─ models/
│  ├─ file_record.py
│  └─ result_models.py
├─ config/
│  └─ classify_rules.json
├─ docs/
│  ├─ spec.md
│  └─ refactor_map.md
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

## 補足
このパックは、既存実装をシンプルな構造へ寄せるための整理済みたたき台です。
機能の入口・構成・責務分離を整えることを目的にしています。
