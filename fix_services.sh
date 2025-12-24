#!/bin/bash

echo "=== systemctl reset-failed ==="
sudo systemctl reset-failed
echo ""

echo "=== systemctl daemon-reload ==="
sudo systemctl daemon-reload
echo ""

echo "=== hostapd 起動 ==="
sudo systemctl start hostapd
sleep 2
sudo systemctl status hostapd --no-pager
echo ""

echo "=== dnsmasq 起動 ==="
sudo systemctl start dnsmasq
sleep 2
sudo systemctl status dnsmasq --no-pager
echo ""

echo "=== 最新ログ ==="
journalctl -e -n 50 --no-pager
echo ""

echo "=== wlan1 状態 ==="
ip addr show wlan1
echo ""

echo "=== hostapd_cli status ==="
sudo hostapd_cli status 2>&1 || echo "(hostapd が起動していません)"
echo ""

echo "=== ポート確認 ==="
ss -tlnup | grep -E "5000|dnsmasq"
