#!/bin/bash
# ラズパイ温度ネットワークシステム - セットアップスクリプト

echo "================================"
echo "ラズパイ温度ネットワークシステム セットアップ"
echo "================================"
echo ""

# Pythonが必要
echo "🔍 Python3をチェック..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3がインストールされていません"
    echo "以下を実行してください:"
    echo "sudo apt-get update && sudo apt-get install python3 python3-pip -y"
    exit 1
fi

echo "✅ Python3がインストール済み"
echo ""

# 必要なPythonライブラリをインストール
echo "📦 Pythonライブラリをインストール中..."
pip3 install flask flask-cors

# ディレクトリ構造を作成
echo "📁 ディレクトリを作成中..."
mkdir -p /home/pi/temperature_server/templates
cd /home/pi/temperature_server

# データベースディレクトリのパーミッション設定
chmod 755 /home/pi/

echo ""
echo "================================"
echo "セットアップ完了！"
echo "================================"
echo ""
echo "次のステップ："
echo "1. server.py をこのディレクトリにコピー"
echo "2. templates/dashboard.html をコピー"
echo "3. python3 server.py を実行"
echo ""
echo "ブラウザで http://ラズパイのIP:5000 にアクセス"
echo ""
