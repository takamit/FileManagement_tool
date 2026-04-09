# リファクタリング方針

## 結論
現在の `app/` は分割しすぎです。  
責務ごとに細かく切られているように見えて、実際には `gui.py` が大きく、周辺モジュールも小粒に散っているため、保守性が落ちています。

## 現在の主な問題
- `app/gui.py` が大きすぎる
- `ui/` と `app/` が重複
- 小さな helper モジュールが多すぎる
- ログ・設定・履歴・進捗が細かく散りすぎて追いにくい

## 推奨する統合後の構成
### app/gui.py
- 画面構築
- ユーザー操作受付
- 表示更新
- バックグラウンド処理の起動

### app/scanner.py
以下を統合:
- classifier.py
- compare_detector.py
- duplicate_detector.py
- filename_analyzer.py
- hasher.py
- series_detector.py
- version_detector.py

### app/executor.py
以下を統合:
- backup_manager.py
- history_manager.py
- report.py
- report_manager.py
- runtime_control.py

### app/services.py
以下を統合:
- config_manager.py
- settings_manager.py
- logger_service.py
- log_manager.py
- progress_service.py
- content_tools.py
- utils.py

## 削除推奨
- ui/
- README.txt
- __pycache__/ 一式
- logs/
- reports/
- backup/
- history/
- config/settings.json（Git 管理から除外）

## 残すべきもの
- app/
- models/
- config/classify_rules.json
- docs/spec.md
- README.md
- requirements.txt
- main.py

## 実装優先順
1. `ui/` を削除して `app/` に一本化
2. `executor.py` をバックアップ / Undo の中核に統合
3. `scanner.py` に判定系を寄せる
4. `services.py` に周辺管理を集約
5. `gui.py` は UI 専用へ寄せる
