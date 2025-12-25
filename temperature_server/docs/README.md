# 🌡️ Dual WiFi Temperature Monitoring System

**リアルタイム温度監視システム：デュアル WiFi（AP + Station）で ESP32 から Raspberry Pi へのデータ送信**

> 本プロジェクトは、単一ボード上で **2つの独立した WiFi ネットワーク** を実現し、IoT デバイスのデータ収集インフラを構築するための完全なガイドです。

---

## 🎯 システム概要

```
┌──────────────┐                    ┌──────────────────┐
│   ESP32      │ WiFi (AP接続)      │  Raspberry Pi 4  │
│ 温度センサー  │ ◄──────────────►  │  Flask Server    │
│ (192.168.4)  │ wlan1: AP 管理     │  SQLite DB       │
└──────────────┘                    │  Web Dashboard   │
                                    └────────┬─────────┘
                                             │
                                    WiFi (Station)
                                    wlan0: インターネット
                                    (192.168.11.x)
```

---

## ✨ 主な特徴

- ✅ **デュアル WiFi 実装**：AP (アクセスポイント) + Station (インターネット接続)
- ✅ **リアルタイム監視**：30秒ごとにデータ収集
- ✅ **Web ダッシュボード**：ブラウザでリアルタイム表示
- ✅ **SQLite データベース**：長期データ保存
- ✅ **自動管理**：systemd サービスで自動起動・再起動
- ✅ **スケーラブル**：複数の ESP32 デバイスに対応可能

---

## 🔧 システム構成

### ハードウェア
- **Raspberry Pi 4** (2GB RAM 以上推奨)
- **USB WiFi ドングル**：TP-Link Archer T2U Plus (RTL8821AU チップセット)
- **ESP32 マイコンボード**：DS18B20 温度センサー搭載

### ソフトウェア
- **OS**: Debian 13 (Raspberry Pi OS)
- **Python**: 3.13
- **Flask**: Web フレームワーク
- **SQLite**: データベース
- **systemd**: サービス管理

### ネットワーク設定
- **wlan0** (オンボード WiFi): Station モード
  - 既存 WiFi ネットワークに接続
  - IP: 192.168.11.x (DHCP)
  
- **wlan1** (USB WiFi): AP モード
  - ESP32 接続用 Access Point
  - SSID: `RaspberryPi_Temperature`
  - IP: 192.168.4.1/24
  - DHCP レンジ: 192.168.4.2-254

---

## 🚀 クイックスタート

### 1. 必要なハードウェアの確認
```bash
# USB WiFi ドングルが認識されているか確認
lsusb | grep -i "tp-link\|realtek"

# インターフェースの確認
ip link show
```

### 2. セットアップスクリプトの実行
```bash
cd ~/temperature_server
sudo bash setup.sh
```

### 3. サービス開始
```bash
sudo systemctl start temperature-server
sudo systemctl status temperature-server
```

### 4. Web ダッシュボードにアクセス
```
http://192.168.11.57:5000/
```

---

## 📚 ドキュメント構成

| ドキュメント | 内容 |
|-------------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | システムアーキテクチャと設計方針 |
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | 完全セットアップガイド（初心者向け） |
| [WIFI_SETUP.md](WIFI_SETUP.md) | デュアル WiFi 設定の詳細解説 |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 問題解決ガイド |
| [ESP32_CODE.md](ESP32_CODE.md) | ESP32 側の実装詳細 |
| [LESSONS_LEARNED.md](LESSONS_LEARNED.md) | 開発過程で学んだ教訓 |

---

## 🔍 主要ファイル構成

```
temperature_server/
├── app/                           # Flask アプリケーション
│   ├── __init__.py               # アプリ初期化・ルート設定
│   ├── flask_app.py              # Flask インスタンス生成
│   └── routes/
│       ├── api.py                # REST API エンドポイント
│       ├── dashboard.py          # Web UI
│       └── wifi.py               # WiFi 管理 API
├── services/
│   ├── wifi_manager.py           # WiFi 設定・管理 ★重要★
│   ├── background_tasks.py       # バックグラウンドタスク
│   └── __init__.py
├── database/
│   ├── models.py                 # DB スキーマ定義
│   ├── queries.py                # DB クエリ
│   └── __init__.py
├── config.py                      # 設定ファイル
├── run.py                         # メイン起動スクリプト
├── setup.sh                       # セットアップスクリプト
└── docs/                          # ドキュメント（このフォルダ）
```

---

## 📊 API エンドポイント

### 温度データ送信（ESP32 側）
```http
POST /api/temperature HTTP/1.1
Host: 192.168.4.1:5000
Content-Type: application/json

{
  "device_id": "ESP32_01",
  "name": "プロトタイプ01",
  "location": "リビング",
  "temperature": 23.5
}
```

### 最新データ取得（Web UI 側）
```http
GET /api/sensors HTTP/1.1
Host: 192.168.4.1:5000
```

---

## 🐛 よくある問題と解決策

### ESP32 がデータを送信できない
→ [TROUBLESHOOTING.md#esp32-connection-refused](TROUBLESHOOTING.md)

### Flask が 192.168.4.1 で受け付けていない
→ [WIFI_SETUP.md#network-routing](WIFI_SETUP.md)

### WiFi health check による不意の再起動
→ [LESSONS_LEARNED.md#health-check-trap](LESSONS_LEARNED.md)

---

## 💡 このシステムから学べること

1. **デュアル WiFi の実装方法**
   - 1 つのボード上で 2 つの独立したネットワーク
   - オンボード WiFi と USB ドングルの併用

2. **Python Flask での REST API 設計**
   - JSON ベースのデータ送受信
   - CORS 対応の Web ダッシュボード

3. **Linux systemd サービス化**
   - 自動起動・再起動の実装
   - ログ管理と監視

4. **IoT デバイス統合**
   - マイコンボード ↔ Raspberry Pi の通信
   - データベースでの時系列データ管理

---

## 📈 パフォーマンス

| メトリクス | 値 |
|-----------|-----|
| データ送信周期 | 30 秒 |
| API レスポンス時間 | < 100ms |
| メモリ使用量 | ~150MB |
| CPU 使用率 | < 5% |
| データベースサイズ | 増加率 ~1MB/月 |

---

## 🔐 セキュリティに関する注意

⚠️ **本システムは開発用・学習用です。本番環境での使用には以下の改善が必要です：**

- [ ] HTTPS/SSL 暗号化
- [ ] API 認証（JWT トークン等）
- [ ] WiFi パスワード強化
- [ ] ファイアウォール設定
- [ ] データベースアクセス制限

---

## 📝 ライセンス

MIT License

---

## 🤝 貢献

改善提案・バグ報告は Issue で受け付けています。

---

## 📞 サポート

問題が発生した場合は、以下の順序で確認してください：

1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を確認
2. [LESSONS_LEARNED.md](LESSONS_LEARNED.md) で似た事例を探す
3. Issue を作成

---

**最後に更新**: 2025年12月24日
