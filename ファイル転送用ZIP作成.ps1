# 変更したファイルをZIPにまとめるスクリプト（USBメモリ転送用）

$SourceDir = "temperature_server"
$OutputZip = "webui_高速化_ファイル.zip"
$Files = @(
    "templates/dashboard.html",
    "templates/stream.html",
    "app/routes/api.py",
    "database/queries.py"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "WebUI高速化ファイル ZIP作成" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 一時ディレクトリを作成
$TempDir = "temp_zip_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

Write-Host "▶ ファイルをコピー中..." -ForegroundColor Yellow
foreach ($File in $Files) {
    $SourcePath = Join-Path $SourceDir $File
    $DestPath = Join-Path $TempDir $File
    $DestDir = Split-Path $DestPath -Parent
    
    if (Test-Path $SourcePath) {
        New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
        Copy-Item $SourcePath $DestPath -Force
        Write-Host "  ✅ $File" -ForegroundColor Green
    } else {
        Write-Host "  ❌ ファイルが見つかりません: $SourcePath" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "▶ ZIPファイルを作成中..." -ForegroundColor Yellow

# ZIPファイルを作成
if (Test-Path $OutputZip) {
    Remove-Item $OutputZip -Force
}

Compress-Archive -Path "$TempDir\*" -DestinationPath $OutputZip -Force

# 一時ディレクトリを削除
Remove-Item $TempDir -Recurse -Force

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "完了" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "ZIPファイル: $OutputZip" -ForegroundColor Green
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Yellow
Write-Host "1. $OutputZip をUSBメモリにコピー" -ForegroundColor White
Write-Host "2. USBメモリをラズパイに接続" -ForegroundColor White
Write-Host "3. ラズパイで解凍してファイルを配置" -ForegroundColor White
Write-Host ""

