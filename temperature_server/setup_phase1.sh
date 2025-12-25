#!/bin/bash
# Temperature Server - Phase 1 自動セットアップスクリプト
# Debian 13 (trixie) 対応

set -e  # エラーで停止

PROJECT_DIR="$HOME/temperature_server"
LOG_FILE="$PROJECT_DIR/setup.log"

echo "=========================================="
echo "🔧 Temperature Server Phase 1 Setup"
echo "=========================================="
echo "Target: Debian 13 (trixie)"
echo "Project: $PROJECT_DIR"
echo ""

# ログを記録
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

# ステップ 1: パッケージ更新
echo "[1/7] パッケージを更新中..."
sudo apt update -qq
sudo apt upgrade -y -qq

# ステップ 2: 必要なシステムパッケージをインストール
echo "[2/7] システムパッケージをインストール中..."
sudo apt install -y -qq \
    python3 python3-pip python3-venv \
    git build-essential \
    hostapd dnsmasq wireless-tools \
    sqlite3 libsqlite3-dev \
    libssl-dev libffi-dev \
    libharfbuzz0b libopenjp2-7 libtiff6 \
    curl wget

# ステップ 3: Python 仮想環境を作成
echo "[3/7] Python 仮想環境を作成中..."
cd "$PROJECT_DIR"
python3 -m venv venv --upgrade-deps
source venv/bin/activate

# ステップ 4: Python パッケージをインストール
echo "[4/7] Python パッケージをインストール中..."
pip install --upgrade pip setuptools wheel -q
pip install -r requirements.txt -q

# ステップ 5: データベースを初期化
echo "[5/7] データベースを初期化中..."
python3 -c "from database.models import init_database; init_database(); print('✓ Database initialized')"

# ステップ 6: ログディレクトリを作成
echo "[6/7] ログディレクトリを作成中..."
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/data"
chmod 755 "$PROJECT_DIR/logs"
chmod 755 "$PROJECT_DIR/data"

# ステップ 7: Systemd サービスを登録
echo "[7/7] Systemd サービスを登録中..."
sudo cp "$PROJECT_DIR/systemd/temperature-server.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable temperature-server

# CLI コマンドのシンボリックリンクを作成
sudo ln -sf "$PROJECT_DIR/cli/management_cli.py" /usr/local/bin/temp-manage
sudo chmod +x /usr/local/bin/temp-manage

echo ""
echo "=========================================="
echo "✅ セットアップ完了!"
echo "=========================================="
echo ""
echo "次のステップ:"
echo "  1. サービスを開始: sudo systemctl start temperature-server"
echo "  2. ステータス確認: sudo systemctl status temperature-server"
echo "  3. ダッシュボード: http://localhost:5000/"
echo "  4. ログ確認: tail -f $PROJECT_DIR/logs/temperature_server.log"
echo ""
echo "CLI コマンド例:"
echo "  temp-manage status      # システムステータス"
echo "  temp-manage wifi-status # WiFi 状態確認"
echo "  temp-manage temp        # 温度統計表示"
echo ""
echo "ログファイル: $LOG_FILE"
echo ""
