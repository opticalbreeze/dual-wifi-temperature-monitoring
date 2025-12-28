#!/bin/bash
# Guest2-Repeater 起動スクリプト

# 実行ユーザーを確認
if [ "$EUID" -eq 0 ]; then 
   echo "エラー: rootユーザーで実行しないでください"
   exit 1
fi

# sudo権限の確認
if ! sudo -n true 2>/dev/null; then
    echo "警告: sudo権限の設定が確認できません"
    echo "        パスワードを入力してください"
    sudo -v
fi

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# venv を有効化
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "エラー: .venv が見つかりません"
    exit 1
fi

# Python環境の確認
if ! command -v python3 &> /dev/null; then
    echo "エラー: Python3がインストールされていません"
    exit 1
fi

# Xvfb（仮想フレームバッファ）を起動
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
XVFB_PID=$!
sleep 2

# メインプログラムを実行
echo "Guest2-Repeaterを起動しています..."
python3 main.py

# Xvfbをクリーンアップ
kill $XVFB_PID 2>/dev/null



