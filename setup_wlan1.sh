#!/bin/bash
# wlan1 AP設定スクリプト
# このスクリプトは起動時に自動実行され、wlan1をAPモード用に設定します

set -e

# NetworkManagerがwlan1を管理しないように設定
nmcli device set wlan1 managed no 2>/dev/null || true

# 既存のIPアドレスを削除
ip addr flush dev wlan1 2>/dev/null || true

# 正しいIPアドレスを設定
ip addr add 192.168.4.1/24 dev wlan1

# インターフェースを有効化
ip link set wlan1 up

# ログ出力
logger "wlan1 AP設定完了: 192.168.4.1/24"

