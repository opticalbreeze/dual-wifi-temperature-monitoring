# Raspberry Pi Dual WiFi Monitoring System

ESP32温度監視システムとWiFi中継器を統合したプロジェクトです。

## 機能

### 1. 温度監視サーバー (temperature_server)
- ESP32温度センサーからのデータ収集
- Web UIによるリアルタイム表示
- 温度アラート機能（設定可能な範囲）
- カメラストリーミング対応

### 2. WiFi中継器 (free_wifi)
- キャプティブポータル自動認証
- インターネット接続監視
- 自動再接続機能

## システム構成

```
Raspberry Pi
├── wlan0: インターネット接続（クライアントモード）
└── wlan1: ESP32接続用AP（192.168.4.1）
```

## クイックスタート

### 1. システム要件

- Raspberry Pi 3B以上（推奨: Pi 4B 4GB）
- Raspberry Pi OS (64bit)
- 2つのWiFiアダプタ
- 4GB以上のRAM

### 2. セットアップ

```bash
# プロジェクトをクローン
git clone https://github.com/opticalbreeze/dual-wifi-temperature-monitoring.git
cd dual-wifi-temperature-monitoring

# デュアルWiFi設定
sudo ./setup_dual_wifi.sh

# 統合環境セットアップ
./setup_unified_venv.sh

# データベース初期化
source venv/bin/activate
cd temperature_server
python3 -c "from database.models import init_database; init_database()"
cd ..

# サービス設定
sudo ./install_wlan1_setup.sh
sudo cp temperature_server/systemd/temperature-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable temperature-server.service
sudo systemctl start temperature-server.service
```

### 3. アクセス

- 温度監視ダッシュボード: http://<ラズパイのIP>:5000
- カメラストリーミング: http://<ラズパイのIP>:5000/stream
- ESP32接続用AP: SSIDはhostapd.confで設定

## ドキュメント

詳細なドキュメントは `docs/` ディレクトリを参照してください。

- [SETUP.md](docs/SETUP.md): 新規ラズパイでのセットアップガイド
- [DUAL_WIFI_SETUP.md](docs/DUAL_WIFI_SETUP.md): デュアルWiFi設定手順（詳細）
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md): トラブルシューティング
- [ESP32_SETUP.md](docs/ESP32_SETUP.md): ESP32コード・設定ガイド
- [ENVIRONMENT_VARIABLES.md](docs/ENVIRONMENT_VARIABLES.md): 環境変数設定ガイド
- [ARCHITECTURE.md](docs/ARCHITECTURE.md): アーキテクチャ詳細

## 使用方法

### 手動起動

```bash
source venv/bin/activate

# 温度サーバー起動
./start_temperature_server.sh

# FREE_Wifi起動（別ターミナル）
./start_free_wifi.sh
```

### サービスとして起動

```bash
# 温度サーバー
sudo systemctl start temperature-server

# FREE_Wifi（オプション）
sudo systemctl start guest2-repeater

# サービス状態確認
sudo systemctl status temperature-server
```

### 診断・メンテナンス

```bash
# システム診断
sudo bash scripts/diagnose.sh

# サービス再起動
sudo bash scripts/restart_services.sh

# サービス修復
sudo bash scripts/fix_services.sh
```

## ライセンス

（必要に応じてライセンスを追加）

## 貢献

（必要に応じて貢献ガイドを追加）

