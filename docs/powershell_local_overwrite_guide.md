# PowerShell 上書き配置手順書

この手順書は、既存の `FileManagement_tool` ローカル環境へ、この成果物を**上書き配置**して、
そのまま起動確認・テスト・GitHub 反映まで進めるためのものです。

前提:

- 既存ローカルリポジトリがある
- Windows + PowerShell を使用する
- 仮想環境は `.venv` を使用する
- 実行場所は **プロジェクト親フォルダ** を基準にする

---

## 1. 置き換え前の想定パス

例:

```powershell
C:\Users\<USER>\Desktop\git project\FileManagement_tool
```

このフォルダが、既存の Git 管理対象プロジェクト本体です。

---

## 2. ZIP を展開する場所

ZIP は既存プロジェクトの**外側**へ展開してください。

例:

```powershell
C:\Users\<USER>\Desktop\git project\file_management_tool_local_ready
```

既存フォルダの中へ直接展開しないでください。
いきなり上書きすると、何を潰したのか分からなくなるからです。

---

## 3. PowerShell で移動

```powershell
cd "C:\Users\<USER>\Desktop\git project"
```

---

## 4. 退避フォルダを作成

```powershell
New-Item -ItemType Directory -Force -Path ".\_backup_before_overwrite"
```

日時付きで退避したい場合:

```powershell
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory -Force -Path ".\_backup_before_overwrite\$stamp"
```

---

## 5. 既存プロジェクトを丸ごと退避

```powershell
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item ".\FileManagement_tool" ".\_backup_before_overwrite\$stamp\FileManagement_tool" -Recurse -Force
```

---

## 6. 新しい成果物を既存プロジェクトへ反映

### 方法A: 中身だけを既存フォルダへ上書きコピー

```powershell
Copy-Item ".\file_management_tool_local_ready\*" ".\FileManagement_tool" -Recurse -Force
```

これで、既存の `.git` は維持したまま、中身だけ更新できます。

### 方法B: 既存フォルダを残しつつ比較してから反映

```powershell
robocopy ".\file_management_tool_local_ready" ".\FileManagement_tool" /E /R:1 /W:1
```

`robocopy` の方が、件数確認や差分確認がしやすいです。

---

## 7. 不要なキャッシュを削除

```powershell
Get-ChildItem ".\FileManagement_tool" -Directory -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem ".\FileManagement_tool" -Recurse -Include "*.pyc" | Remove-Item -Force
```

---

## 8. プロジェクトへ移動

```powershell
cd ".\FileManagement_tool"
```

---

## 9. `.venv` を作成または再作成

既に `.venv` があるなら流用でも構いません。
不安なら作り直してください。

### 新規作成

```powershell
python -m venv .venv
```

### 有効化

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 10. 依存関係を反映

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 11. 起動確認

### CLI ヘルプ

```powershell
python main.py --mode cli --help
```

### GUI 起動

```powershell
python main.py --mode gui
```

---

## 12. テスト実行

```powershell
pytest
```

---

## 13. Git 差分確認

```powershell
git status
git diff --stat
```

README・docs・ディレクトリ構成が設計書準拠へ寄っているか、ここで確認します。

---

## 14. GitHub 反映

```powershell
git add .
git commit -m "refactor: align local structure with development specification"
git push origin main
```

ブランチ運用を厳格にするなら、設計書どおり `feature/*` や `fix/*` を使ってください。

---

## 15. 一括コピペ用コマンド

`<USER>` 部分だけ自分の環境に合わせて置換してください。

```powershell
cd "C:\Users\<USER>\Desktop\git project"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory -Force -Path ".\_backup_before_overwrite\$stamp" | Out-Null
Copy-Item ".\FileManagement_tool" ".\_backup_before_overwrite\$stamp\FileManagement_tool" -Recurse -Force
robocopy ".\file_management_tool_local_ready" ".\FileManagement_tool" /E /R:1 /W:1
Get-ChildItem ".\FileManagement_tool" -Directory -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem ".\FileManagement_tool" -Recurse -Include "*.pyc" | Remove-Item -Force
cd ".\FileManagement_tool"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pytest
git status
git diff --stat
```

---

## 16. 補足

この成果物では、README と docs 配下の Markdown も、設計書の内容が分かるように更新済みです。
ただし、既存資産由来の `legacy_*.md` も残しているため、**新しい運用では README / local_setup / github_overwrite_guide / powershell_local_overwrite_guide / specification_alignment を優先して参照**してください。
