# FileManagement Tool

## 概要
2つのフォルダ（対象 / 比較）を比較し、不要ファイルの削除・更新・整理を安全かつ効率的に行う Python 製 GUI ツールです。

## この再構成版の方針
- 既存機能を落とさないことを最優先
- 実行時生成物は Git 管理から除外
- README は入口、詳細は `docs/` に分離
- 更新処理は `move` 固定、バックアップ前提
- 既存のモジュール分割は維持し、機能喪失を避ける

## 主な機能
- フォルダ再帰スキャン
- フィルタ / ソート / 選択
- 差分分類（同一、更新候補、同名同サイズ、同名別内容、サイズ差分）
- zip 軽量解析（展開なし）
- 削除（ゴミ箱）
- 更新（move）
- バックアップ / Undo
- 進捗表示

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

## ディレクトリ構成
```text
FileManagement_tool/
├─ app/                  # 本体ロジック
├─ models/               # データモデル
├─ config/               # ルール定義
├─ docs/                 # 仕様 / 引継ぎ / 今後の整理方針
├─ ui/                   # 旧UI資産（互換確認が終わるまで保持）
├─ main.py
├─ requirements.txt
├─ README.md
└─ .gitignore
```

## 補足
`app/` のファイル数は多いですが、今は無理に統合していません。前回のように機能を落とす方がまずいからです。まずはこの構成で復旧し、その後に段階的に整理するのが安全です。
