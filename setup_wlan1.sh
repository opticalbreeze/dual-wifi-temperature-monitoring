#!/bin/bash
# wlan1 AP設定スクリプト
# このスクリプトは起動時に自動実行され、wlan1をAPモード用に設定します

set -e

# 環境変数から設定を読み込み（デフォルト値: 192.168.4.1/24）
AP_IP="${AP_IP:-192.168.4.1}"
AP_SUBNET="${AP_SUBNET:-24}"
AP_INTERFACE="${AP_INTERFACE:-wlan1}"

# NetworkManagerがwlan1を管理しないように設定
nmcli device set ${AP_INTERFACE} managed no 2>/dev/null || true

# 既存のIPアドレスを削除
ip addr flush dev ${AP_INTERFACE} 2>/dev/null || true

# IPアドレスを設定
ip addr add ${AP_IP}/${AP_SUBNET} dev ${AP_INTERFACE}

# インターフェースを有効化
ip link set ${AP_INTERFACE} up

# ログ出力
logger "wlan1 AP設定完了: ${AP_IP}/${AP_SUBNET}"

