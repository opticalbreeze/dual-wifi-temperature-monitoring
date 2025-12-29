#!/bin/bash
# wlan1 AP設定スクリプト
# このスクリプトは起動時に自動実行され、wlan1をAPモード用に設定します
# ⚠️ 現地操作専用 - リモート実行禁止

# リモート実行の検出（systemd経由の実行時はSSH_CONNECTIONが設定されないため、起動時のみ実行可能）
# ただし、手動実行時はリモート実行を検出
if [ -n "$SSH_CONNECTION" ] || [ -n "$SSH_CLIENT" ]; then
    echo "❌ エラー: このスクリプトはSSH経由で実行できません。"
    echo "現地操作（HDMI/キーボード）またはsystemd経由でのみ実行可能です。"
    exit 1
fi

set -e

# 環境変数から設定を読み込み（デフォルト値: 192.168.4.1/24）
AP_IP="${AP_IP:-192.168.4.1}"
AP_SUBNET="${AP_SUBNET:-24}"
AP_INTERFACE="${AP_INTERFACE:-wlan1}"

# 接続経路の確認（wlan1が接続に使われていないか確認）
DEFAULT_IF=$(ip route show default 2>/dev/null | awk '{print $5}' | head -1)
if [ "$DEFAULT_IF" = "$AP_INTERFACE" ]; then
    echo "❌ エラー: $AP_INTERFACE がデフォルトゲートウェイとして使用されています。"
    echo "実行を中止します。"
    exit 1
fi

# NetworkManagerがwlan1を管理しないように設定（永続化）
# 1. 一時的な設定
nmcli device set ${AP_INTERFACE} managed no 2>/dev/null || true

# 2. 永続的な設定ファイルを作成
NM_CONF_DIR="/etc/NetworkManager/conf.d"
NM_CONF_FILE="${NM_CONF_DIR}/99-unmanaged-wlan1.conf"
if [ ! -f "${NM_CONF_FILE}" ]; then
    echo "[keyfile]" | sudo tee "${NM_CONF_FILE}" > /dev/null
    echo "unmanaged-devices=interface-name:${AP_INTERFACE}" | sudo tee -a "${NM_CONF_FILE}" > /dev/null
    # NetworkManagerの設定をリロード
    sudo systemctl reload NetworkManager 2>/dev/null || true
    logger "NetworkManager永続化設定を作成: ${NM_CONF_FILE}"
fi

# 既存のIPアドレスを削除
ip addr flush dev ${AP_INTERFACE} 2>/dev/null || true

# IPアドレスを設定
ip addr add ${AP_IP}/${AP_SUBNET} dev ${AP_INTERFACE}

# インターフェースを有効化
ip link set ${AP_INTERFACE} up

# wpa_supplicantがwlan1に自動接続しないようにする
# wlan1用のwpa_supplicantプロセスを停止（存在する場合）
sudo pkill -f "wpa_supplicant.*${AP_INTERFACE}" 2>/dev/null || true

# ログ出力
logger "wlan1 AP設定完了: ${AP_IP}/${AP_SUBNET}"

