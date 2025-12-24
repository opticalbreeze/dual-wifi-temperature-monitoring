#!/bin/bash
# Temperature Server - デプロイスクリプト
# ローカルマシンから Raspberry Pi に展開

TARGET_HOST="${1:-192.168.11.57}"
TARGET_USER="${2:-pi}"
TARGET_DIR="$HOME/temperature_server"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "📦 Deploying Temperature Server"
echo "=========================================="
echo "Source: $SOURCE_DIR"
echo "Target: $TARGET_USER@$TARGET_HOST:$TARGET_DIR"
echo ""

# SSH 接続テスト
if ! ssh -q -o ConnectTimeout=3 "$TARGET_USER@$TARGET_HOST" exit; then
    echo "❌ Cannot connect to $TARGET_HOST"
    echo "Please ensure:"
    echo "  1. Raspberry Pi is powered on"
    echo "  2. SSH is enabled (raspi-config)"
    echo "  3. Network is accessible"
    exit 1
fi

# ファイル転送
echo "[1/3] Transferring files..."
scp -r "$SOURCE_DIR/temperature_server" "$TARGET_USER@$TARGET_HOST:~/" || {
    echo "❌ File transfer failed"
    exit 1
}

# セットアップスクリプト実行
echo "[2/3] Running setup script..."
ssh "$TARGET_USER@$TARGET_HOST" "bash ~/temperature_server/setup_phase1.sh" || {
    echo "⚠️  Setup had issues (check logs)"
}

# ステータス確認
echo "[3/3] Verifying installation..."
ssh "$TARGET_USER@$TARGET_HOST" "python3 ~/temperature_server/cli/management_cli.py status" || true

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps on Raspberry Pi:"
echo "  1. sudo systemctl start temperature-server"
echo "  2. Visit http://192.168.11.57:5000/"
echo ""
