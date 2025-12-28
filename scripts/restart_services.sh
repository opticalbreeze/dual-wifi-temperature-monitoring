#!/bin/bash
# Raspberry Pi システム再起動スクリプト
# 使用方法: sudo bash scripts/restart_services.sh

echo "=========================================="
echo "デュアル WiFi 温度監視システム"
echo "サービス再起動スクリプト"
echo "=========================================="
echo ""

# wlan1-setup 再起動
echo "▶ wlan1-setup サービスを再起動します..."
sudo systemctl restart wlan1-setup.service
sleep 2
echo ""
echo "=== wlan1-setup ステータス ==="
sudo systemctl status wlan1-setup.service --no-pager | head -10
echo ""

# Flask サーバー再起動
echo "▶ Flask サーバー (temperature-server) を再起動します..."
sudo systemctl restart temperature-server
sleep 2
echo ""
echo "=== Flask サーバー ステータス ==="
sudo systemctl status temperature-server --no-pager | head -10
echo ""

# hostapd 再起動
echo "▶ hostapd (WiFi AP) を再起動します..."
sudo systemctl restart hostapd
sleep 2
echo ""
echo "=== hostapd ステータス ==="
sudo systemctl status hostapd --no-pager | head -10
echo ""

# dnsmasq 再起動
echo "▶ dnsmasq (DHCP) を再起動します..."
sudo systemctl restart dnsmasq
sleep 2
echo ""
echo "=== dnsmasq ステータス ==="
sudo systemctl status dnsmasq --no-pager | head -10
echo ""

# ネットワーク確認
echo "=========================================="
echo "ネットワーク設定確認"
echo "=========================================="
echo ""

echo "▶ wlan0 (Station) - 既存ネットワーク接続"
ip addr show wlan0 | grep -E "inet |state" || echo "(wlan0 が見つかりません)"
echo ""

echo "▶ wlan1 (AP) - ESP32 用アクセスポイント"
ip addr show wlan1 | grep -E "inet |state" || echo "(wlan1 が見つかりません)"
echo ""

echo "▶ WiFi AP に接続しているクライアント:"
sudo iw dev wlan1 station dump 2>/dev/null | grep -A 20 "Station" || echo "(クライアントが見つかりません)"
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

