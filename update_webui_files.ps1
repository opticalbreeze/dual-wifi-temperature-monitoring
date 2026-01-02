# WebUI高速化の変更ファイルをラズパイに転送するPowerShellスクリプト

$REMOTE_HOST = "raspberry@192.168.1.93"
$REMOTE_DIR = "/home/raspberry/temperature_monitoring/temperature_server"
$BASE_DIR = "temperature_server"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "WebUI高速化ファイル転送スクリプト" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 変更したファイルリスト
$FILES = @(
    "templates/dashboard.html",
    "templates/stream.html",
    "app/routes/api.py",
    "database/queries.py"
)

# 1. 各ファイルを転送
Write-Host "▶ ファイルをリモートサーバーに転送中..." -ForegroundColor Yellow
foreach ($FILE in $FILES) {
    $LOCAL_FILE = Join-Path $BASE_DIR $FILE
    $REMOTE_FILE = "$REMOTE_DIR/$FILE"
    
    if (-not (Test-Path $LOCAL_FILE)) {
        Write-Host "  ❌ ファイルが見つかりません: $LOCAL_FILE" -ForegroundColor Red
        continue
    }
    
    Write-Host "  転送中: $FILE" -ForegroundColor Gray
    scp $LOCAL_FILE "${REMOTE_HOST}:${REMOTE_FILE}"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ❌ 転送失敗: $FILE" -ForegroundColor Red
    } else {
        Write-Host "  ✅ 転送完了: $FILE" -ForegroundColor Green
    }
}
Write-Host ""

# 2. リモートサーバーで実行中のプロセスを確認
Write-Host "▶ 実行中のサーバープロセスを確認中..." -ForegroundColor Yellow
$PID = ssh $REMOTE_HOST "ps aux | grep 'python.*run.py' | grep -v grep | awk '{print `$2}'"
if ([string]::IsNullOrEmpty($PID)) {
    Write-Host "⚠️  実行中のサーバープロセスが見つかりません" -ForegroundColor Yellow
    Write-Host "   手動でサーバーを起動してください:" -ForegroundColor Yellow
    Write-Host "   ssh $REMOTE_HOST 'cd $REMOTE_DIR && source venv/bin/activate && python run.py'" -ForegroundColor Gray
} else {
    Write-Host "✅ プロセスID: $PID" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  サーバーを再起動する場合は、以下のコマンドを実行してください:" -ForegroundColor Yellow
    Write-Host "   ssh $REMOTE_HOST 'cd $REMOTE_DIR && pkill -f \"python.*run.py\" && sleep 2 && source venv/bin/activate && nohup python run.py > server.log 2>&1 &'" -ForegroundColor Gray
}
Write-Host ""

# 3. 転送されたファイルの確認
Write-Host "▶ 転送されたファイルを確認中..." -ForegroundColor Yellow
foreach ($FILE in $FILES) {
    $REMOTE_FILE = "$REMOTE_DIR/$FILE"
    ssh $REMOTE_HOST "test -f $REMOTE_FILE && echo '  ✅ $FILE' || echo '  ❌ $FILE (見つかりません)'"
}
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "転送完了" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Yellow
Write-Host "1. サーバーを再起動（必要に応じて）" -ForegroundColor White
Write-Host "2. ブラウザで http://192.168.1.93:5000 にアクセスして動作確認" -ForegroundColor White
Write-Host "3. ログを確認: ssh $REMOTE_HOST 'tail -f $REMOTE_DIR/logs/app.routes.api.log'" -ForegroundColor White
Write-Host ""

