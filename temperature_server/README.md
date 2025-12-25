# 🌡️ Temperature Server - Raspberry Pi

Raspberry Pi + ESP32 温度センサー統合システム

## 🎯 機能

- ✅ WiFi AP（ESP32 接続用）
- ✅ WiFi クライアント（インターネット接続用）
- ✅ USB WiFi ドングル自動接続（自由 WiFi）
- ✅ ビデオストリーミング（複数解像度）
- ✅ Tailscale 遠隔管理
- ✅ 温度データ履歴管理
- ✅ メモリリーク防止機構
- ✅ ワンクリック管理画面

## 📋 インストール手順

### 1. Raspberry Pi OS セットアップ

```bash
# パッケージ更新
sudo apt update && sudo apt upgrade -y

# 必要なパッケージインストール
sudo apt install -y python3-pip git hostapd dnsmasq wireless-tools

# Python 環境
sudo pip3 install --upgrade pip setuptools wheel
```

### 2. プロジェクト配置

```bash
cd ~
git clone <your-repo> temperature_server
cd temperature_server
```

### 3. Python 依存パッケージ

```bash
pip3 install -r requirements.txt
```

### 4. データベース初期化

```bash
python3 -c "from database.models import init_database; init_database()"
```

### 5. Systemd サービス登録

```bash
sudo cp systemd/temperature-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable temperature-server
sudo systemctl start temperature-server

# ステータス確認
sudo systemctl status temperature-server
```

## 🚀 使用方法

### Web UI
- 📊 ダッシュボード: http://192.168.4.1:5000/
- 🎥 ストリーミング: http://192.168.4.1:5000/stream
- ⚙️ 管理画面: http://192.168.4.1:5000/management

### CLI コマンド

```bash
# システムステータス表示
python3 cli/management_cli.py status

# WiFi スキャン
python3 cli/management_cli.py wifi-scan

# 温度統計表示
python3 cli/management_cli.py temp

# メモリ状況表示
python3 cli/management_cli.py memory

# キャッシュクリア
python3 cli/management_cli.py clear-cache

# サービス再起動
python3 cli/management_cli.py restart
```

## 📁 ディレクトリ構造

```
temperature_server/
├── app/                      # Flask アプリケーション
│   ├── routes/              # ルート定義
│   ├── static/              # 静的ファイル
│   └── templates/           # HTML テンプレート
├── database/                # データベース層
│   ├── models.py           # スキーマ定義
│   └── queries.py          # クエリ操作
├── cli/                     # コマンドラインツール
├── services/                # ビジネスロジック
├── config.py               # 設定ファイル
├── logger.py               # ロギング設定
├── run.py                  # メインエントリーポイント
└── requirements.txt        # Python 依存パッケージ
```

## 🔧 設定

`config.py` で以下を調整可能:

```python
# WiFi 設定
WIFI_SSID = "RaspberryPi_Temperature"
WIFI_PASSWORD = "RaspberryPi2025"

# メモリ警告
MEMORY_THRESHOLD = 80  # %

# ビデオ解像度
AVAILABLE_RESOLUTIONS = {
    '360p': (640, 360, 24),
    '720p': (1280, 720, 24),
    '1080p': (1920, 1080, 30)
}
```

## 📊 API エンドポイント

### 温度データ送信 (POST)
```bash
curl -X POST http://localhost:5000/api/temperature \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_id": "esp32_01",
    "sensor_name": "居間",
    "temperature": 25.5,
    "humidity": 60
  }'
```

### 最新データ取得 (GET)
```bash
curl http://localhost:5000/api/sensors
```

### センサー詳細 (GET)
```bash
curl "http://localhost:5000/api/temperature/esp32_01?hours=24"
```

## 🐛 トラブルシューティング

### WiFi AP が起動しない

```bash
# ステータス確認
sudo systemctl status hostapd
sudo systemctl status dnsmasq

# ログ確認
sudo journalctl -u hostapd -n 20
sudo journalctl -u dnsmasq -n 20

# 手動起動テスト
sudo hostapd -d /etc/hostapd/hostapd.conf
```

### メモリ使用率が高い

```bash
# メモリ状況確認
python3 cli/management_cli.py memory

# キャッシュクリア
python3 cli/management_cli.py clear-cache
```

### サーバーが起動しない

```bash
# ログを確認
tail -f logs/temperature_server.log

# 手動起動でエラー表示
python3 run.py
```

## 🔐 セキュリティ

- ✅ WPA2 暗号化 WiFi
- ✅ 定期的なログローテーション
- ✅ メモリリーク防止
- ✅ Tailscale 遠隔管理

## 📝 ライセンス

MIT

## 📞 サポート

問題が発生した場合は、`logs/` ディレクトリのログを確認してください。
