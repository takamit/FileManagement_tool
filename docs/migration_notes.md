# 旧構成からの移行メモ

## 主な変更点

- `models/` → `core/models/`
- `core/` 直下の機能群 → `core/logic`, `core/services`, `core/utils` に整理
- `main.py` → 起動分岐専用へ変更
- `ui/components/`, `logs/`, `data/`, `tests/` を補完
- `.venv` 前提の `.gitignore` へ更新

## 互換性維持の考え方

既存の import 影響を抑えるため、既存モジュール名は可能な範囲で残しています。
同時に、設計書の読みやすさを担保するため、以下のラッパーを追加しています。

- `core/logic/file_management_logic.py`
- `core/services/file_scanner_service.py`
- `core/services/file_operation_service.py`
- `core/services/backup_service.py`
- `core/utils/logger.py`
- `core/utils/path_validator.py`
- `config/app_config.py`
- `config/logging_config.py`

## 今後の整理候補

- GUI の部品分割
- `settings_manager.py` の config 層寄せ
- 実行履歴やレポート出力のサービス境界整理
