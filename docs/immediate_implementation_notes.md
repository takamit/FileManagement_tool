# 今回の即時実装内容

## 1. 更新方式の安全化
- `選択側のファイルで更新` を **コピー更新** に変更
- `選択側のファイルで更新（移動）` は従来互換として維持
- どちらもバックアップを取得してから置換

## 2. CLI の強化
- `--action scan|preview|export-preview|apply|undo-last` を追加
- `--dry-run` を追加
- `--report` / `--report-format` を追加
- `--undo-manifest` を追加

## 3. 設定管理の強化
- デフォルト設定を追加
- 破損した `settings.json` を退避
- 型不正や値不正を正規化
- 履歴件数 `history_limit` を設定で管理

## 4. バックアップ履歴の改善
- 履歴保持上限を 50 件に拡張可能にした
- `metadata` を manifest / index に保持
- `update_copy` / `update_move` を区別して Undo を分岐

## 5. テスト追加
- 安全なコピー更新
- 移動更新の互換性
- dry-run の無変更性
- 設定バリデーション
- CLI preview / undo-last

## 反映方法
この差分ファイル群を既存リポジトリの同名パスへ上書きしてください。
