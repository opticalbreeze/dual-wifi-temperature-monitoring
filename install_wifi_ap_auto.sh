#!/bin/bash
# WiFi AP 自動化のインストール
# 使用方法: sudo bash install_wifi_ap_auto.sh

set -e

if [ "$EUID" -ne 0 ]; then
    echo "❌ このスクリプトは sudo で実行してください"
    exit 1
fi

echo "================================"
echo "WiFi AP 自動起動のセットアップ"
echo "================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ステップ1: スクリプトをコピー
echo "📋 スクリプトをシステムディレクトリにコピー中..."
cp "$SCRIPT_DIR/setup_ap_auto.sh" /usr/local/bin/setup_ap_auto.sh
chmod +x /usr/local/bin/setup_ap_auto.sh
echo "✅ スクリプトのコピー完了"
echo ""

# ステップ2: systemd サービスをコピー
echo "📋 systemd サービスをコピー中..."
cp "$SCRIPT_DIR/setup-wifi-ap.service" /etc/systemd/system/setup-wifi-ap.service
chmod 644 /etc/systemd/system/setup-wifi-ap.service
echo "✅ サービスファイルのコピー完了"
echo ""

# ステップ3: systemd リロード
echo "🔄 systemd を リロード中..."
systemctl daemon-reload
echo "✅ systemd リロード完了"
echo ""

# ステップ4: サービスを有効化
echo "⚙️ サービスを有効化中..."
systemctl enable setup-wifi-ap.service
echo "✅ サービスを有効化完了"
echo ""

# ステップ5: IP フォワーディング永続化
echo "⚙️ IP フォワーディングを永続化中..."
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
fi
sysctl -p > /dev/null 2>&1
echo "✅ IP フォワーディング永続化完了"
echo ""

echo "================================"
echo "✅ セットアップ完了"
echo "================================"
echo ""
echo "📝 使用方法："
echo ""
echo "1️⃣ 今すぐ AP を起動する："
echo "   sudo bash $SCRIPT_DIR/fix_ap.sh"
echo ""
echo "2️⃣ ラズパイを再起動（自動実行確認）："
echo "   sudo reboot"
echo ""
echo "3️⃣ AP が起動しているか確認："
echo "   iwconfig wlan1"
echo "   ip addr show wlan1"
echo ""
echo "⚠️ サービスのステータス確認："
echo "   systemctl status setup-wifi-ap"
echo ""
