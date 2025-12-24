#!/bin/bash
# WiFi AP 自動起動スクリプト
# ブート時に自動実行される

sleep 5  # ネットワーク初期化を待つ

# wlan1 に IP アドレス設定
ip addr flush dev wlan1 2>/dev/null || true
sleep 1
ip addr add 192.168.4.1/24 dev wlan1 2>/dev/null || true

# IP フォワーディング有効化
sysctl -w net.ipv4.ip_forward=1 > /dev/null 2>&1

# iptables NAT ルール設定
iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE 2>/dev/null || true
iptables -A FORWARD -i wlan1 -o wlan0 -j ACCEPT 2>/dev/null || true
iptables -A FORWARD -i wlan0 -o wlan1 -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true

# サービス再起動
systemctl restart dnsmasq 2>/dev/null || true
sleep 2
systemctl restart hostapd 2>/dev/null || true

exit 0
