# FileManagement Tool

## 概要

Python製のGUIファイル管理ツール。
2つのフォルダ（対象 / 比較）を比較し、不要ファイルの削除・更新・整理を安全かつ効率的に行う。

---

## 主な機能

* フォルダ再帰スキャン（非同期・UI非ブロッキング）
* ファイル差分の自動分類
* zip軽量解析（展開なし）
* フィルタ・ソート・選択機能
* 削除 / 更新（move）処理
* バックアップおよびUndo対応
* 進捗表示

---

## 分類カテゴリ

* 同一ファイル
* 更新候補
* 同名同サイズ
* 同名別内容
* サイズ差分

---

## セットアップ

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## 実行

```bash
python main.py
```

---

## ディレクトリ構成

```text
FileManagement_tool/
├─ app/                # GUI / ロジック
├─ models/             # データモデル
├─ config/             # 設定ファイル
├─ docs/               # ドキュメント
│   └─ spec.md         # 詳細仕様
├─ main.py
├─ requirements.txt
├─ README.md
└─ .gitignore
```

---

## ドキュメント

詳細仕様は以下を参照：

* docs/spec.md

---

## 注意

このツールはファイルの削除・移動を伴います。
重要なデータに対して使用する前にバックアップを推奨します。
