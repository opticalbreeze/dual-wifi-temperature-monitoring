#!/bin/bash
# FREE_Wifi起動スクリプト（統合環境用）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 仮想環境をアクティベート
if [ ! -d "venv" ]; then
    echo "エラー: 仮想環境が見つかりません。先に ./setup_unified_venv.sh を実行してください。"
    exit 1
fi

source venv/bin/activate

# free_wifiディレクトリに移動して起動
cd free_wifi
python3 main.py

