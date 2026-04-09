# 安全な整理方針

## 結論
前回のように骨格だけへ置換すると機能が消えるため、今回は**既存のモジュール分割を維持**する。

## 今回やったこと
- 既存の `app/`, `models/`, `ui/` を保持
- 実行時生成物（logs, reports, backup, history, __pycache__）を除外
- `README.md`, `docs/spec.md`, `.gitignore` を追加 / 整備
- `app/executor.py` の更新処理だけ安全に修正

## 次段階でやること
1. `ui/` が実際に未使用かを確認
2. `app/gui.py` を機能単位で分割
3. scanner まわりの判定ロジックを整理
4. 周辺管理クラスの統合を検討

## ローカルの正しい構成
```text
FileManagement_tool/
├─ app/
├─ models/
├─ config/
├─ docs/
├─ ui/
├─ main.py
├─ requirements.txt
├─ README.md
└─ .gitignore
```

## Git 管理から外すもの
```text
venv/
__pycache__/
logs/
reports/
backup/
history/
config/settings.json
```
