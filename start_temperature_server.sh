#!/bin/bash
# 温度サーバー起動スクリプト（統合環境用）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 仮想環境をアクティベート
if [ ! -d "venv" ]; then
    echo "エラー: 仮想環境が見つかりません。先に ./setup_unified_venv.sh を実行してください。"
    exit 1
fi

source venv/bin/activate

# temperature_serverディレクトリに移動して起動
cd temperature_server
python3 run.py

