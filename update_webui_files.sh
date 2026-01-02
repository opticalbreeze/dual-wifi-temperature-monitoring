#!/bin/bash
# WebUI高速化の変更ファイルをラズパイに転送するスクリプト

REMOTE_HOST="raspberry@192.168.1.93"
REMOTE_DIR="/home/raspberry/temperature_monitoring/temperature_server"
BASE_DIR="temperature_server"

echo "=========================================="
echo "WebUI高速化ファイル転送スクリプト"
echo "=========================================="
echo ""

# 変更したファイルリスト
FILES=(
    "templates/dashboard.html"
    "templates/stream.html"
    "app/routes/api.py"
    "database/queries.py"
)

# 1. 各ファイルを転送
echo "▶ ファイルをリモートサーバーに転送中..."
for FILE in "${FILES[@]}"; do
    LOCAL_FILE="$BASE_DIR/$FILE"
    REMOTE_FILE="$REMOTE_DIR/$FILE"
    
    if [ ! -f "$LOCAL_FILE" ]; then
        echo "❌ ファイルが見つかりません: $LOCAL_FILE"
        continue
    fi
    
    echo "  転送中: $FILE"
    scp "$LOCAL_FILE" "$REMOTE_HOST:$REMOTE_FILE"
    if [ $? -ne 0 ]; then
        echo "  ❌ 転送失敗: $FILE"
    else
        echo "  ✅ 転送完了: $FILE"
    fi
done
echo ""

# 2. リモートサーバーで実行中のプロセスを確認
echo "▶ 実行中のサーバープロセスを確認中..."
PID=$(ssh "$REMOTE_HOST" "ps aux | grep 'python.*run.py' | grep -v grep | awk '{print \$2}'")
if [ -z "$PID" ]; then
    echo "⚠️  実行中のサーバープロセスが見つかりません"
    echo "   手動でサーバーを起動してください:"
    echo "   ssh $REMOTE_HOST 'cd $REMOTE_DIR && source venv/bin/activate && python run.py'"
else
    echo "✅ プロセスID: $PID"
    echo ""
    echo "⚠️  サーバーを再起動する場合は、以下のコマンドを実行してください:"
    echo "   ssh $REMOTE_HOST 'cd $REMOTE_DIR && pkill -f \"python.*run.py\" && sleep 2 && source venv/bin/activate && nohup python run.py > server.log 2>&1 &'"
fi
echo ""

# 3. 転送されたファイルの確認
echo "▶ 転送されたファイルを確認中..."
for FILE in "${FILES[@]}"; do
    REMOTE_FILE="$REMOTE_DIR/$FILE"
    ssh "$REMOTE_HOST" "test -f $REMOTE_FILE && echo '  ✅ $FILE' || echo '  ❌ $FILE (見つかりません)'"
done
echo ""

echo "=========================================="
echo "転送完了"
echo "=========================================="
echo ""
echo "次のステップ:"
echo "1. サーバーを再起動（必要に応じて）"
echo "2. ブラウザで http://192.168.1.93:5000 にアクセスして動作確認"
echo "3. ログを確認: ssh $REMOTE_HOST 'tail -f $REMOTE_DIR/logs/app.routes.api.log'"
echo ""

