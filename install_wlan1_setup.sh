#!/bin/bash
# wlan1自動設定のインストールスクリプト
# このスクリプトを実行すると、起動時に自動的にwlan1が設定されます

set -e

echo "=== wlan1自動設定のインストール ==="

# スクリプトを/usr/local/binにコピー
sudo cp setup_wlan1.sh /usr/local/bin/setup_wlan1.sh
sudo chmod +x /usr/local/bin/setup_wlan1.sh

# systemdサービスファイルをコピー
sudo cp wlan1-setup.service /etc/systemd/system/wlan1-setup.service

# systemdをリロード
sudo systemctl daemon-reload

# サービスを有効化
sudo systemctl enable wlan1-setup.service

# サービスを起動（テスト）
sudo systemctl start wlan1-setup.service

# 状態確認
echo ""
echo "=== インストール完了 ==="
echo "サービス状態:"
sudo systemctl status wlan1-setup.service --no-pager | head -10

echo ""
echo "wlan1の状態:"
ip addr show wlan1 | grep inet || echo "wlan1が見つかりません"

echo ""
echo "再起動後も自動的にwlan1が設定されます。"

