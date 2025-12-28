#!/bin/bash
# 統合仮想環境セットアップスクリプト

set -e

echo "=== 統合仮想環境のセットアップ ==="

# 既存のvenvを削除（オプション）
if [ -d "venv" ]; then
    read -p "既存のvenvを削除しますか？ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "既存のvenvを削除しています..."
        rm -rf venv
    fi
fi

# 仮想環境の作成
if [ ! -d "venv" ]; then
    echo "仮想環境を作成しています..."
    python3 -m venv venv
fi

# 仮想環境をアクティベート
source venv/bin/activate

# pipをアップグレード
echo "pipをアップグレードしています..."
pip install --upgrade pip

# 統合requirements.txtをインストール
echo "依存パッケージをインストールしています..."
pip install -r requirements.txt

echo ""
echo "=== セットアップ完了 ==="
echo "仮想環境をアクティベート: source venv/bin/activate"

