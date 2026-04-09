# FileManagement Tool

## 概要

Python製のGUIファイル管理ツールです。
2つのフォルダ（対象 / 比較）を比較し、不要ファイルの削除・更新・整理を安全かつ効率的に行うことを目的としています。

## 主な機能

* フォルダ再帰スキャン
* UI非ブロッキング処理
* フィルタ対応
* ファイル差分分類
* zip軽量解析
* 削除・更新処理
* バックアップ / Undo対応
* 進捗表示

## 主な分類

* 同一ファイル
* 更新候補
* 同名同サイズ
* 同名別内容
* サイズ差分

## 設計上の重要ルール

* 表示されている行のみ操作対象
* 更新処理は copy 禁止、move 必須
* zip は展開せず一覧のみ参照
* UI とロジックは分離する

## ディレクトリ構成

```text
FileManagement_tool/
├─ app/
│  ├─ gui.py
│  ├─ scanner.py
│  └─ executor.py
├─ config/
├─ docs/
│  └─ spec.md
├─ main.py
├─ requirements.txt
├─ README.md
└─ .gitignore
```

## セットアップ

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 実行

```bash
python main.py
```

## ドキュメント

詳細仕様は以下を参照してください。

* `docs/spec.md`

## 注意

このツールは削除・移動処理を伴います。
重要データに対して使用する前に、バックアップを取得してください。
