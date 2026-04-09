# refactor_plan

## このパックで反映した修正
- `app/gui.py` を `ui/gui.py` へ移設
- `app/` のロジック群を `core/` へ移設
- `main.py` の起動先を `ui.gui` に変更
- `ui/` と `core/` の責務を明確化
- `executor.py` の move 更新失敗時に、バックアップからの復元処理を追加
- `README.txt`、`__pycache__`、`logs/`、`reports/`、`backup/`、`history/` などの生成物を除外

## 注意
- 既存機能維持を最優先にしているため、内部ロジックの大規模統合までは行っていない
- まずはこの構造で動作確認し、その後に `core/` の再整理を行う
