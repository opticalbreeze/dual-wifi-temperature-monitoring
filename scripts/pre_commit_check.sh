#!/bin/bash
# スクリプト作成時の自動チェック
# このスクリプトは危険なコマンドを含むスクリプトを検出します

SCRIPT_PATH="$1"

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "ファイルが見つかりません: $SCRIPT_PATH"
    exit 1
fi

SCRIPT_CONTENT=$(cat "$SCRIPT_PATH")

# チェック項目
ERRORS=0
WARNINGS=0

echo "=== スクリプト安全性チェック: $SCRIPT_PATH ==="
echo ""

# 1. 危険なコマンドのチェック
echo "1. 危険なコマンドのチェック..."
DANGEROUS=(
    "killall"
    "pkill.*wpa_supplicant"
    "systemctl stop wpa_supplicant"
    "systemctl stop NetworkManager"
)

for cmd in "${DANGEROUS[@]}"; do
    if echo "$SCRIPT_CONTENT" | grep -qE "$cmd"; then
        echo "  ❌ 危険: $cmd が検出されました"
        ERRORS=$((ERRORS + 1))
    fi
done

# 2. リモート実行検出のチェック
echo "2. リモート実行検出機能のチェック..."
if ! echo "$SCRIPT_CONTENT" | grep -qE "SSH_CONNECTION|SSH_CLIENT"; then
    if echo "$SCRIPT_CONTENT" | grep -qE "ip addr|ip link|nmcli|systemctl.*restart.*hostapd|systemctl.*restart.*dnsmasq"; then
        echo "  ⚠️  警告: リモート実行検出機能がありません"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# 3. 警告メッセージのチェック
echo "3. 警告メッセージのチェック..."
if echo "$SCRIPT_CONTENT" | grep -qE "ip addr|ip link|nmcli"; then
    if ! echo "$SCRIPT_CONTENT" | grep -qE "警告|WARNING|⚠️"; then
        echo "  ⚠️  警告: 警告メッセージがありません"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# 4. 確認プロンプトのチェック
echo "4. 確認プロンプトのチェック..."
if echo "$SCRIPT_CONTENT" | grep -qE "ip addr|ip link|nmcli"; then
    if ! echo "$SCRIPT_CONTENT" | grep -qE "read.*続行|read.*continue|y/N"; then
        echo "  ⚠️  警告: 確認プロンプトがありません"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# 結果
echo ""
echo "=== チェック結果 ==="
echo "エラー: $ERRORS"
echo "警告: $WARNINGS"

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "❌ このスクリプトは危険です。修正してください。"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo ""
    echo "⚠️  警告があります。確認してください。"
    exit 0
else
    echo ""
    echo "✅ チェック完了"
    exit 0
fi


