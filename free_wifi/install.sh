#!/bin/bash
# Guest2-Repeater インストールスクリプト for Raspbian（ラズビアン）専用

set -e  # エラーが発生したら終了

echo "========================================="
echo " Guest2-Repeater インストールスクリプト"
echo "========================================="
echo ""

# rootユーザーで実行されていないか確認
if [ "$EUID" -eq 0 ]; then 
   echo "エラー: rootユーザーで実行しないでください"
   exit 1
fi

echo "1. システムのアップデート..."
sudo apt-get update
sudo apt-get -y upgrade

echo ""
echo "2. 必要なパッケージをインストール..."
sudo apt-get -y install python3 python3-pip python3-tk chromium-browser chromium-chromedriver

echo ""
echo "3. Python3の依存パッケージをインストール..."
pip3 install selenium requests

echo ""
echo "4. Chromedriverのパスを確認..."
if [ -f "/usr/bin/chromedriver" ]; then
    echo "✓ /usr/bin/chromedriver が存在します"
elif [ -f "/usr/lib/chromium-browser/chromedriver" ]; then
    echo "✓ /usr/lib/chromium-browser/chromedriver が存在します"
    # シンボリックリンクを作成
    sudo ln -s /usr/lib/chromium-browser/chromedriver /usr/bin/chromedriver
else
    echo "警告: chromedriverが見つかりません"
fi

echo ""
echo "5. sudo権限の設定..."
echo "このアプリケーションはWi-Fi制御と再起動コマンドでsudo権限が必要です"
echo "パスワードなしでsudoを実行できるように設定しますか？ (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "sudo設定中..."
    sudo bash -c "echo '$(whoami) ALL=(ALL) NOPASSWD: /usr/sbin/rfkill, /usr/sbin/reboot, /usr/bin/chromedriver' > /etc/sudoers.d/guest2-repeater"
    sudo chmod 0440 /etc/sudoers.d/guest2-repeater
    echo "✓ sudo設定完了"
else
    echo "⚠ sudoのパスワード入力が必要になります"
fi

echo ""
echo "6. 起動スクリプトに実行権限を付与..."
chmod +x start.sh

echo ""
echo "========================================="
echo " インストール完了"
echo "========================================="
echo ""
echo "使用方法:"
echo "  ./start.sh を実行してください"
echo ""
echo "設定変更:"
echo "  config.py を編集してください"
echo ""



