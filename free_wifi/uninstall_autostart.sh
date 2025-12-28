#!/bin/bash
# Guest2-Repeater 自動起動解除スクリプト for Raspbian

set -e

echo "========================================="
echo " Guest2-Repeater 自動起動解除"
echo "========================================="
echo ""

# rootユーザーで実行されていないか確認
if [ "$EUID" -eq 0 ]; then 
   echo "エラー: rootユーザーで実行しないでください"
   exit 1
fi

SERVICE_NAME="guest2-repeater.service"

# サービスが有効かどうか確認
if systemctl is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
    echo "サービスを停止しています..."
    sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    
    echo "サービスを無効化しています..."
    sudo systemctl disable "$SERVICE_NAME"
    
    echo "✓ サービスを無効化しました"
else
    echo "サービスは既に無効化されています"
fi

# サービスファイルを削除するか確認
read -p "サービスファイルを削除しますか？ (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
    if [ -f "$SERVICE_FILE" ]; then
        sudo rm "$SERVICE_FILE"
        sudo systemctl daemon-reload
        echo "✓ サービスファイルを削除しました"
    else
        echo "サービスファイルが見つかりません"
    fi
fi

echo ""
echo "========================================="
echo " 自動起動解除完了"
echo "========================================="
echo ""

