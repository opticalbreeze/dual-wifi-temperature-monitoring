#!/bin/bash
# WiFi AP の修復・起動スクリプト
# dhcpcd がない環境対応版
# 使用方法: sudo bash fix_ap.sh

set -e

echo "================================"
echo "WiFi AP 修復スクリプト"
echo "================================"
echo ""

# root 確認
if [ "$EUID" -ne 0 ]; then
    echo "❌ このスクリプトは sudo で実行してください"
    exit 1
fi

# ステップ1: wlan1 に IP アドレス設定
echo "⚙️ wlan1 に IP アドレスを設定中..."
ip addr flush dev wlan1 2>/dev/null || true
sleep 1
ip addr add 192.168.4.1/24 dev wlan1 || echo "⚠️ IP アドレスは既に設定されています"
echo "✅ IP アドレス設定完了"
echo ""

# ステップ2: IP フォワーディング有効化
echo "⚙️ IP フォワーディングを有効化中..."
sysctl -w net.ipv4.ip_forward=1 > /dev/null
echo "✅ IP フォワーディング有効化完了"
echo ""

# ステップ3: iptables NAT ルール設定
echo "⚙️ iptables ルールを設定中..."
iptables -t nat -D POSTROUTING -o wlan0 -j MASQUERADE 2>/dev/null || true
iptables -D FORWARD -i wlan1 -o wlan0 -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -i wlan0 -o wlan1 -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true

iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
iptables -A FORWARD -i wlan1 -o wlan0 -j ACCEPT
iptables -A FORWARD -i wlan0 -o wlan1 -m state --state RELATED,ESTABLISHED -j ACCEPT
echo "✅ iptables ルール設定完了"
echo ""

# ステップ4: サービス再起動
echo "⚙️ サービスを再起動中..."
systemctl restart dnsmasq
sleep 2
systemctl restart hostapd
sleep 2
echo "✅ サービス再起動完了"
echo ""

# ステップ5: 状態確認
echo "================================"
echo "✅ WiFi AP 修復完了"
echo "================================"
echo ""
echo "📊 状態確認："
echo ""
echo "wlan1 IP アドレス:"
ip addr show wlan1 | grep "inet "
echo ""
echo "hostapd ステータス:"
systemctl status hostapd | grep "Active"
echo ""
echo "dnsmasq ステータス:"
systemctl status dnsmasq | grep "Active"
echo ""
echo "================================"
