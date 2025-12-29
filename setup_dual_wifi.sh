#!/bin/bash
# デュアルWiFi設定スクリプト（新規ラズパイ用）
# ⚠️ 現地操作専用 - リモート実行禁止

# リモート実行の検出
if [ -n "$SSH_CONNECTION" ] || [ -n "$SSH_CLIENT" ]; then
    echo "❌ エラー: このスクリプトはSSH経由で実行できません。"
    echo "現地操作（HDMI/キーボード）が必要です。"
    exit 1
fi

set -e

# 環境変数から設定を読み込み（デフォルト値: 192.168.4.1/24）
AP_IP="${AP_IP:-192.168.4.1}"
AP_SUBNET="${AP_SUBNET:-24}"
AP_INTERFACE="${AP_INTERFACE:-wlan1}"

echo "=== デュアルWiFi設定セットアップ ==="
echo ""
echo "⚠️  警告: このスクリプトはネットワーク設定を変更します。"
echo "このスクリプトは以下を設定します："
echo "- wlan0: インターネット接続（クライアントモード）"
echo "- ${AP_INTERFACE}: ESP32接続用AP（${AP_IP}/${AP_SUBNET}）"
echo ""
echo "接続経路を確認中..."
DEFAULT_IF=$(ip route show default 2>/dev/null | awk '{print $5}' | head -1)
if [ "$DEFAULT_IF" = "$AP_INTERFACE" ]; then
    echo "❌ エラー: $AP_INTERFACE がデフォルトゲートウェイとして使用されています。"
    echo "実行を中止します。"
    exit 1
fi
echo "デフォルトゲートウェイ: $DEFAULT_IF (OK)"
echo ""
read -p "続行しますか？ (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# 必要なパッケージのインストール
echo "必要なパッケージをインストールしています..."
sudo apt update
sudo apt install -y hostapd dnsmasq network-manager

# wlan1の設定
echo ""
echo "${AP_INTERFACE}インターフェースを確認しています..."
if ! ip link show ${AP_INTERFACE} > /dev/null 2>&1; then
    echo "エラー: ${AP_INTERFACE}インターフェースが見つかりません。"
    echo "USB WiFiアダプタが接続されているか確認してください。"
    exit 1
fi

# NetworkManagerがwlan1を管理しないように設定
echo "NetworkManagerが${AP_INTERFACE}を管理しないように設定しています..."
sudo nmcli device set ${AP_INTERFACE} managed no

# wlan1のIPアドレスを設定
echo "${AP_INTERFACE}のIPアドレスを設定しています..."
sudo ip addr flush dev ${AP_INTERFACE} 2>/dev/null || true
sudo ip addr add ${AP_IP}/${AP_SUBNET} dev ${AP_INTERFACE}
sudo ip link set ${AP_INTERFACE} up

# hostapd設定ファイルの確認
if [ ! -f "hostapd.conf" ]; then
    echo "警告: hostapd.confが見つかりません。"
    echo "手動で設定してください。"
else
    echo "hostapd設定を確認しています..."
    sudo cp hostapd.conf /etc/hostapd/hostapd.conf
    echo "DAEMON_CONF=\"/etc/hostapd/hostapd.conf\"" | sudo tee -a /etc/default/hostapd
fi

# dnsmasq設定の確認
if [ ! -f "dnsmasq.conf" ]; then
    echo "警告: dnsmasq.confが見つかりません。"
    echo "手動で設定してください。"
else
    echo "dnsmasq設定を確認しています..."
    sudo cp dnsmasq.conf /etc/dnsmasq.conf
fi

# サービスを有効化
echo "サービスを有効化しています..."
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq

# wlan1自動設定サービスをインストール
if [ -f "install_wlan1_setup.sh" ]; then
    echo "wlan1自動設定サービスをインストールしています..."
    chmod +x install_wlan1_setup.sh
    sudo ./install_wlan1_setup.sh
fi

# サービスを再起動
echo "サービスを再起動しています..."
sudo systemctl restart hostapd
sudo systemctl restart dnsmasq

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "設定を確認:"
ip addr show ${AP_INTERFACE} | grep inet
sudo systemctl status hostapd --no-pager | head -5
echo ""
echo "再起動後も自動的に${AP_INTERFACE}が設定されます。"
echo ""
echo "環境変数でカスタマイズする場合:"
echo "  export AP_IP=192.168.4.1"
echo "  export AP_SUBNET=24"
echo "  export AP_INTERFACE=wlan1"

