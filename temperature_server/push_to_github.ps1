# GitHub Push Script for PowerShell
# このスクリプトを PowerShell で実行してください：
# powershell -ExecutionPolicy Bypass -File push_to_github.ps1

param(
    [string]$RepositoryUrl = "https://github.com/opticalbreeze/dual-wifi-temperature-monitoring.git",
    [string]$RepoPath = "i:\ESP32DS18\raspberry_pi\temperature_server"
)

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host ("=" * 60)
    Write-Host "▶ $Message"
    Write-Host ("=" * 60)
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error-Message {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Run-Command {
    param(
        [string]$Command,
        [string]$Description = ""
    )
    
    if ($Description) {
        Write-Header $Description
    }
    
    Write-Host "$ $Command" -ForegroundColor Cyan
    
    try {
        Invoke-Expression $Command 2>&1
        Write-Success "実行完了"
        return $true
    } catch {
        Write-Error-Message "エラー: $_"
        return $false
    }
}

# Main script
Write-Host ""
Write-Host "デュアル WiFi 温度監視システム - GitHub Push" -ForegroundColor Cyan -BackgroundColor DarkBlue
Write-Host "リポジトリ URL: $RepositoryUrl" -ForegroundColor Yellow
Write-Host "パス: $RepoPath" -ForegroundColor Yellow
Write-Host ""

# Check if directory exists
if (-not (Test-Path $RepoPath)) {
    Write-Error-Message "ディレクトリが見つかりません: $RepoPath"
    exit 1
}

# Change to repository directory
Set-Location $RepoPath
Write-Success "ディレクトリに移動: $(Get-Location)"

# Check if git is installed
try {
    $gitVersion = git --version
    Write-Success "Git: $gitVersion"
} catch {
    Write-Error-Message "Git がインストールされていません"
    Write-Host "https://git-scm.com/download/win からインストールしてください"
    exit 1
}

# Initialize git if not already done
if (-not (Test-Path ".git")) {
    Write-Header "Git リポジトリを初期化します"
    Run-Command "git init" | Out-Null
    Run-Command "git config user.name 'Temperature Server Developer'" | Out-Null
    Run-Command "git config user.email 'opticalbreeze@github.com'" | Out-Null
    Write-Success "Git 初期化完了"
} else {
    Write-Success "Git リポジトリは既に初期化されています"
}

# Show current status
Write-Header "現在のステータス"
git status

# Stage all files
Write-Header "ファイルをステージングします"
git add -A
Write-Success "ステージング完了"

# Show staged files
Write-Header "ステージングされたファイル"
git diff --cached --name-only

# Create commit
Write-Header "コミットを作成します"
$commitMessage = @"
Initial commit: Complete dual WiFi temperature monitoring system with comprehensive documentation

- 7 comprehensive markdown documents
- Complete Raspberry Pi dual WiFi setup guide
- RTL8821AU driver installation instructions
- Flask REST API server implementation
- SQLite database with persistent storage
- Real-time web dashboard
- ESP32 microcontroller implementation guide
- 10 lessons learned from 6+ hour development crisis
- Detailed troubleshooting guide
"@

git commit -m $commitMessage
Write-Success "コミット作成完了"

# Configure remote
Write-Header "GitHub リモートを設定します"
try {
    git remote remove origin 2>$null
} catch {}
git remote add origin $RepositoryUrl
Write-Success "リモート URL を設定: $RepositoryUrl"

# Ensure main branch
Write-Header "メインブランチを確認します"
git branch -M main
Write-Success "ブランチ: main"

# Push to GitHub
Write-Header "GitHub にプッシュします"
Write-Host "認証が必要な場合、GitHub の認証情報を入力してください" -ForegroundColor Yellow
Write-Host ""

$pushSuccess = $false
try {
    git push -u origin main -v
    $pushSuccess = $true
} catch {
    Write-Error-Message "プッシュに失敗しました: $_"
}

# Final message
Write-Host ""
Write-Host ("=" * 60)
if ($pushSuccess) {
    Write-Host "✓ プッシュ完了！" -ForegroundColor Green
} else {
    Write-Host "✗ プッシュに失敗しました" -ForegroundColor Red
}
Write-Host ("=" * 60)
Write-Host ""

if ($pushSuccess) {
    Write-Host "リポジトリ URL:" -ForegroundColor Cyan
    Write-Host "https://github.com/opticalbreeze/dual-wifi-temperature-monitoring" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "ドキュメントを確認してください:" -ForegroundColor Cyan
    Write-Host "- https://github.com/opticalbreeze/dual-wifi-temperature-monitoring/blob/main/MAIN_README.md" -ForegroundColor Yellow
} else {
    Write-Host "トラブルシューティング:" -ForegroundColor Yellow
    Write-Host "1. GitHub の認証情報が正しいか確認"
    Write-Host "2. ネットワーク接続を確認"
    Write-Host "3. リポジトリが GitHub に存在するか確認"
    Write-Host ""
    Write-Host "手動でプッシュする場合:"
    Write-Host "git push -u origin main" -ForegroundColor Cyan
}

Write-Host ""
