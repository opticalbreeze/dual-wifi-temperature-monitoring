#!/bin/bash

echo "========================================="
echo "ラズパイ AP 診断スクリプト"
echo "========================================="
echo ""

echo "=== 1. USB デバイス確認 ==="
lsusb | grep -i "wireless\|80211" || echo "(WiFi ドングルが見つかりません)"
echo ""

echo "=== 2. ネットワークインターフェース ==="
ip link show | grep -E "^[0-9]|wlan|eth"
echo ""

echo "=== 3. IPアドレス設定 ==="
ip addr show | grep -E "^[0-9]|inet|wlan"
echo ""

echo "=== 4. hostapd サービス状態 ==="
sudo systemctl status hostapd 2>&1 | head -20
echo ""

echo "=== 5. dnsmasq サービス状態 ==="
sudo systemctl status dnsmasq 2>&1 | head -20
echo ""

echo "=== 6. setup-wifi-ap サービス状態 ==="
sudo systemctl status setup-wifi-ap.service 2>&1 | head -20
echo ""

echo "=== 7. wlan1 の詳細情報 ==="
sudo iwconfig wlan1 2>&1 || echo "(wlan1 が見つかりません)"
echo ""

echo "=== 8. ポート状態確認 ==="
sudo ss -tlnup 2>/dev/null | grep -E "dnsmasq|hostapd|:5000" || echo "（ポート情報が取得できません）"
echo ""

echo "=== 9. hostapd ログ（最新30行） ==="
sudo journalctl -u hostapd -n 30 --no-pager 2>&1 | tail -30
echo ""

echo "=== 10. dnsmasq ログ（最新30行） ==="
sudo journalctl -u dnsmasq -n 30 --no-pager 2>&1 | tail -30
echo ""

echo "========================================="
echo "診断完了"
echo "========================================="
