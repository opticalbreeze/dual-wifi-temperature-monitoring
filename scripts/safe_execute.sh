#!/bin/bash
# 安全なスクリプト実行ラッパー
# このスクリプトは危険なコマンドを検出し、実行を阻止します

SCRIPT_PATH="$1"
shift
ARGS="$@"

# 危険なコマンドのリスト
DANGEROUS_COMMANDS=(
    "killall"
    "pkill.*wpa_supplicant"
    "systemctl stop wpa_supplicant"
    "systemctl stop NetworkManager"
    "ip link set.*down"
    "nmcli device.*set.*wlan0"
    "ip addr flush.*wlan0"
)

# スクリプトの内容をチェック
if [ -f "$SCRIPT_PATH" ]; then
    SCRIPT_CONTENT=$(cat "$SCRIPT_PATH")
    
    for cmd in "${DANGEROUS_COMMANDS[@]}"; do
        if echo "$SCRIPT_CONTENT" | grep -qE "$cmd"; then
            echo "❌ 危険なコマンドが検出されました: $cmd"
            echo "このスクリプトはリモート実行できません。"
            echo "現地操作が必要です。"
            exit 1
        fi
    done
fi

# SSH接続の検出
if [ -n "$SSH_CONNECTION" ] || [ -n "$SSH_CLIENT" ]; then
    # ネットワーク設定を変更する可能性があるコマンドをチェック
    NETWORK_COMMANDS=(
        "ip addr"
        "ip link set"
        "nmcli device set"
        "systemctl restart hostapd"
        "systemctl restart dnsmasq"
    )
    
    for cmd in "${NETWORK_COMMANDS[@]}"; do
        if echo "$SCRIPT_CONTENT" | grep -qE "$cmd"; then
            echo "⚠️  警告: このスクリプトはネットワーク設定を変更します。"
            echo "SSH接続中は実行できません。"
            echo "現地操作が必要です。"
            exit 1
        fi
    done
fi

# 安全な場合のみ実行
exec bash "$SCRIPT_PATH" "$@"


