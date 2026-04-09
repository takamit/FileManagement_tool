# 既存実装の再配置計画

## このパックで反映した修正

- `main.py` を CLI / GUI の起動分岐専用へ整理
- `models/` 相当を `core/models/` へ統一
- `core/` 配下を `logic / services / utils` に整理
- `ui/components/`, `logs/`, `data/`, `tests/` を補完
- 設計書向けのラッパー層を追加
- `.gitignore` を `.venv` 前提へ更新

## 今後の整理案

1. `ui/gui.py` を部品単位で `ui/components/` へ分割
2. サービス層の責務をさらに明確化
3. 設定値を `config/` に段階移行
4. テストを入力検証・異常系まで増強
