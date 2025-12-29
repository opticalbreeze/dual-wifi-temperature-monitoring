#!/bin/bash
# リモートサーバーのapi.pyを更新してサーバーを再起動するスクリプト

REMOTE_HOST="raspberry@192.168.1.93"
REMOTE_DIR="/home/raspberry/temperature_monitoring/temperature_server"
LOCAL_API_FILE="temperature_server/app/routes/api.py"

echo "=========================================="
echo "リモートサーバー更新スクリプト"
echo "=========================================="
echo ""

# 1. ローカルのapi.pyをリモートに転送
echo "▶ api.pyをリモートサーバーに転送中..."
scp "$LOCAL_API_FILE" "$REMOTE_HOST:$REMOTE_DIR/app/routes/api.py"
if [ $? -ne 0 ]; then
    echo "❌ ファイル転送に失敗しました"
    exit 1
fi
echo "✅ 転送完了"
echo ""

# 2. リモートサーバーで実行中のプロセスを確認
echo "▶ 実行中のサーバープロセスを確認中..."
PID=$(ssh "$REMOTE_HOST" "ps aux | grep 'python.*run.py' | grep -v grep | awk '{print \$2}'")
if [ -z "$PID" ]; then
    echo "⚠️  実行中のサーバープロセスが見つかりません"
else
    echo "プロセスID: $PID"
fi
echo ""

# 3. サーバーを再起動
echo "▶ サーバーを再起動中..."
ssh "$REMOTE_HOST" "cd $REMOTE_DIR && pkill -f 'python.*run.py' && sleep 2 && source venv/bin/activate && nohup python run.py > server.log 2>&1 & sleep 3 && echo '✅ サーバー再起動完了'"
echo ""

# 4. サーバーの状態を確認
echo "▶ サーバーの状態を確認中..."
ssh "$REMOTE_HOST" "ps aux | grep 'python.*run.py' | grep -v grep && echo '' && tail -20 $REMOTE_DIR/server.log"
echo ""

echo "=========================================="
echo "完了"
echo "=========================================="
echo ""
echo "ログを確認: ssh $REMOTE_HOST 'tail -f $REMOTE_DIR/logs/app.routes.api.log'"




