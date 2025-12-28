#!/bin/bash
# Guest2-Repeater 自動起動設定スクリプト for Raspbian

set -e

echo "========================================="
echo " Guest2-Repeater 自動起動設定"
echo "========================================="
echo ""

# rootユーザーで実行されていないか確認
if [ "$EUID" -eq 0 ]; then 
   echo "エラー: rootユーザーで実行しないでください"
   exit 1
fi

# 現在のユーザーとホームディレクトリを取得
CURRENT_USER=$(whoami)
HOME_DIR=$(eval echo ~$CURRENT_USER)
PROJECT_DIR="$HOME_DIR/FREE_Wi-Fi中継器コピー"

# プロジェクトディレクトリの存在確認
if [ ! -d "$PROJECT_DIR" ]; then
    echo "エラー: プロジェクトディレクトリが見つかりません: $PROJECT_DIR"
    echo "       プロジェクトを正しい場所に配置してください"
    exit 1
fi

# start.shの存在確認
if [ ! -f "$PROJECT_DIR/start.sh" ]; then
    echo "エラー: start.shが見つかりません: $PROJECT_DIR/start.sh"
    exit 1
fi

echo "現在のユーザー: $CURRENT_USER"
echo "ホームディレクトリ: $HOME_DIR"
echo "プロジェクトディレクトリ: $PROJECT_DIR"
echo ""

# サービスファイルのパスを確認
SERVICE_FILE="/etc/systemd/system/guest2-repeater.service"

# 既存のサービスファイルがあるか確認
if [ -f "$SERVICE_FILE" ]; then
    echo "既存のサービスファイルが見つかりました"
    echo "既存のサービスを停止・無効化します..."
    sudo systemctl stop guest2-repeater.service 2>/dev/null || true
    sudo systemctl disable guest2-repeater.service 2>/dev/null || true
fi

# サービスファイルを作成
echo "サービスファイルを作成しています..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Guest2-Repeater Wi-Fi Repeater for Raspbian
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment="DISPLAY=:0"
Environment="XAUTHORITY=$HOME_DIR/.Xauthority"
ExecStartPre=/bin/sleep 10
ExecStart=/bin/bash $PROJECT_DIR/start.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
EOF

echo "✓ サービスファイルを作成しました: $SERVICE_FILE"
echo ""

# systemdをリロード
echo "systemdをリロードしています..."
sudo systemctl daemon-reload

# サービスを有効化
echo "サービスを有効化しています..."
sudo systemctl enable guest2-repeater.service

echo ""
echo "========================================="
echo " 自動起動設定完了"
echo "========================================="
echo ""
echo "次のコマンドでサービスを管理できます:"
echo ""
echo "  サービスを開始:  sudo systemctl start guest2-repeater.service"
echo "  サービスを停止:  sudo systemctl stop guest2-repeater.service"
echo "  状態を確認:      sudo systemctl status guest2-repeater.service"
echo "  ログを確認:      journalctl -u guest2-repeater.service -f"
echo "  自動起動を無効化: sudo systemctl disable guest2-repeater.service"
echo ""
echo "再起動すると自動的に起動します。"
echo ""

# すぐに起動するか確認
read -p "今すぐサービスを開始しますか？ (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "サービスを開始しています..."
    sudo systemctl start guest2-repeater.service
    sleep 2
    sudo systemctl status guest2-repeater.service --no-pager
fi

