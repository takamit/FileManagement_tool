param(
    [string]$WorkspacePath = "C:\Users\<USER>\Desktop\git project",
    [string]$ProjectName = "FileManagement_tool",
    [string]$PackageFolderName = "file_management_tool_local_ready"
)

$ErrorActionPreference = "Stop"

Set-Location $WorkspacePath

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupRoot = Join-Path $WorkspacePath "_backup_before_overwrite"
$backupPath = Join-Path $backupRoot $stamp
$projectPath = Join-Path $WorkspacePath $ProjectName
$packagePath = Join-Path $WorkspacePath $PackageFolderName

New-Item -ItemType Directory -Force -Path $backupPath | Out-Null
Copy-Item $projectPath (Join-Path $backupPath $ProjectName) -Recurse -Force

robocopy $packagePath $projectPath /E /R:1 /W:1
if ($LASTEXITCODE -gt 7) {
    throw "robocopy failed with exit code $LASTEXITCODE"
}

Get-ChildItem $projectPath -Directory -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem $projectPath -Recurse -Include "*.pyc" | Remove-Item -Force

Set-Location $projectPath

if (-not (Test-Path ".\.venv")) {
    python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" -m pytest

git status
git diff --stat

Write-Host "Overwrite completed successfully."
