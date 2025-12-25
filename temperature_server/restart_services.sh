#!/bin/bash
# Raspberry Pi システム再起動スクリプト
# 使用方法: sudo bash restart_services.sh

echo "=========================================="
echo "デュアル WiFi 温度監視システム"
echo "サービス再起動スクリプト"
echo "=========================================="
echo ""

# Flask サーバー再起動
echo "▶ Flask サーバー (temperature-server) を再起動します..."
sudo systemctl restart temperature-server
sleep 2
echo ""
echo "=== Flask サーバー ステータス ==="
sudo systemctl status temperature-server --no-pager
echo ""

# hostapd 再起動
echo "▶ hostapd (WiFi AP) を再起動します..."
sudo systemctl restart hostapd
sleep 2
echo ""
echo "=== hostapd ステータス ==="
sudo systemctl status hostapd --no-pager
echo ""

# dnsmasq 再起動
echo "▶ dnsmasq (DHCP) を再起動します..."
sudo systemctl restart dnsmasq
sleep 2
echo ""
echo "=== dnsmasq ステータス ==="
sudo systemctl status dnsmasq --no-pager
echo ""

# ネットワーク確認
echo "=========================================="
echo "ネットワーク設定確認"
echo "=========================================="
echo ""

echo "▶ wlan0 (Station) - 既存ネットワーク接続"
ip addr show wlan0 | grep -E "inet |state"
echo ""

echo "▶ wlan1 (AP) - ESP32 用アクセスポイント"
ip addr show wlan1 | grep -E "inet |state"
echo ""

echo "▶ WiFi AP に接続しているクライアント:"
sudo iw dev wlan1 station dump | grep -A 20 "Station"
echo ""

# Flask ログ確認
echo "=========================================="
echo "Flask サーバー ログ（最新 30 行）"
echo "=========================================="
echo ""
sudo journalctl -u temperature-server -n 30 --no-pager
echo ""

# 完了メッセージ
echo "=========================================="
echo "✓ システム再起動完了！"
echo "=========================================="
echo ""
echo "確認項目:"
echo "1. Flask サーバー: http://192.168.4.1:5000"
echo "2. Web ダッシュボード: http://192.168.4.1:5000/"
echo "3. API テスト:"
echo "   curl http://192.168.4.1:5000/api/status"
echo "4. ESP32 接続: 上のクライアント一覧を確認"
echo ""
echo "データベースの確認:"
echo "   sqlite3 temperature_data.db"
echo "   SELECT * FROM temperatures ORDER BY timestamp DESC LIMIT 10;"
echo ""
