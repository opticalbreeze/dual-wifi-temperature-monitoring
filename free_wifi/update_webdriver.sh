#!/bin/bash
# ChromiumとWebドライバーの更新スクリプト

echo "Chromiumとchromedriverを更新しています..."
echo ""

# システムのアップデート
echo "1. システムパッケージのアップデート..."
sudo apt-get -y update
sudo apt-get -y upgrade

# Chromiumとchromedriverのインストール/更新
echo ""
echo "2. Chromiumとchromedriverの更新..."
sudo apt-get -y install chromium-browser chromium-chromedriver

# Chromedriverのパスを確認
echo ""
echo "3. Chromedriverのパスを確認..."
if [ -f "/usr/bin/chromedriver" ]; then
    echo "✓ /usr/bin/chromedriver が利用可能です"
elif [ -f "/usr/lib/chromium-browser/chromedriver" ]; then
    echo "✓ /usr/lib/chromium-browser/chromedriver が利用可能です"
    if [ ! -f "/usr/bin/chromedriver" ]; then
        echo "シンボリックリンクを作成します..."
        sudo ln -s /usr/lib/chromium-browser/chromedriver /usr/bin/chromedriver
    fi
else
    echo "エラー: chromedriverが見つかりません"
    exit 1
fi

echo ""
echo "4. バージョン確認..."
chromium-browser --version
chromedriver --version

echo ""
echo "更新完了"
echo ""



