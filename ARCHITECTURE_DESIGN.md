# ESP32 温度センサー + WiFi ストリーミング システム
## 要件定義 & アーキテクチャ設計書

**作成日:** 2025年12月23日  
**バージョン:** 1.0  
**ステータス:** 設計フェーズ

---

## 1. プロジェクト概要

### 1.1 目的
- Raspberry Pi でローカル WiFi AP (ESP32 接続用) を構築
- フリーWiFi 経由でインターネット接続
- USB カメラでビデオストリーミング
- ESP32 温度センサーデータ収集
- ダッシュボード UI で統合表示
- 遠隔管理機能（Tailscale 経由）

### 1.2 技術スタック
- **OS:** Raspberry Pi OS (初期化済み)
- **Python:** 3.9+
- **Web Framework:** Flask
- **Database:** SQLite
- **WiFi:** Archer T2U Plus (USB ドングル) + 内蔵モジュール
- **Streaming:** OpenCV (mjpg-streamer 代替)
- **遠隔接続:** Tailscale
- **管理 UI:** Flask + Web UI + CLI ツール

---

## 2. システムアーキテクチャ

### 2.1 コンポーネント図

```
┌─────────────────────────────────────────────────────────┐
│                  Raspberry Pi (192.168.11.57)           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Flask Web Server (ポート 5000)                   │  │
│  ├────────┬──────────────┬──────────┬───────────────┤  │
│  │Dashboard│ Streaming   │ API      │ Management UI │  │
│  │温度表示 │ ビデオ配信  │ ESP32受信│ 設定・監視   │  │
│  └────────┴──────────────┴──────────┴───────────────┘  │
│                      ↑                                   │
│  ┌──────────────────┼───────────────────────────────┐  │
│  │  Core Services   │                               │  │
│  ├──────────────────┼───────────────────────────────┤  │
│  │ ┌──────────────┐ ┌──────────────┐               │  │
│  │ │ WiFi Manager │ │ Data Logger  │               │  │
│  │ │ - AP (内蔵)  │ │ - SQLite     │               │  │
│  │ │ - Station    │ │ - Temp data  │               │  │
│  │ │   (USB)      │ │              │               │  │
│  │ └──────────────┘ └──────────────┘               │  │
│  │ ┌──────────────┐ ┌──────────────┐               │  │
│  │ │ WiFi Monitor │ │ Video Capture│               │  │
│  │ │ - selenium   │ │ - OpenCV     │               │  │
│  │ │ - captive    │ │ - USB Camera │               │  │
│  │ │   portal     │ │              │               │  │
│  │ └──────────────┘ └──────────────┘               │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
         ↑                          ↓
    ┌────────┐              ┌────────────────┐
    │ ESP32  │              │ USB Camera     │
    │ (AP)   │              │ (Streaming)    │
    └────────┘              └────────────────┘
```

### 2.2 ネットワーク構成

```
ESP32 (AP)
   ↓
WiFi: RaspberryPi_Temperature (192.168.4.0/24)
   ↓
Raspberry Pi (wlan1)
   ↓
┌─ Archer T2U Plus (USB) → フリーWiFi (192.168.11.x)
│                           ↓
│                       インターネット (Tailscale)
│
└─ 内蔵WiFi (wlan0) → ローカルLAN (192.168.11.57)
                      VNC, SSH 接続用
```

---

## 3. ディレクトリ構成

```
~/temperature_server/
├── README.md
├── requirements.txt
├── config.py                  # グローバル設定
├── main.py                    # エントリーポイント
│
├── app/
│   ├── __init__.py
│   ├── flask_app.py          # Flask アプリケーション
│   ├── routes/
│   │   ├── dashboard.py      # ダッシュボード
│   │   ├── stream.py         # ビデオストリーミング
│   │   ├── api.py            # ESP32 API
│   │   └── management.py     # 管理 UI
│   └── static/
│       ├── js/
│       ├── css/
│       └── images/
│
├── services/
│   ├── __init__.py
│   ├── wifi_manager.py       # WiFi 管理（AP + Station）
│   ├── wifi_monitor.py       # フリーWiFi 監視（selenium）
│   ├── video_capture.py      # ビデオキャプチャ
│   ├── data_logger.py        # SQLite ロギング
│   └── memory_monitor.py     # メモリ監視
│
├── templates/
│   ├── dashboard.html        # 温度ダッシュボード
│   ├── stream.html           # ビデオストリーミング
│   └── management.html       # 管理画面
│
├── database/
│   ├── __init__.py
│   ├── models.py             # SQLite スキーマ
│   └── queries.py            # DB 操作
│
├── cli/
│   ├── __init__.py
│   └── management_cli.py     # CLI 管理ツール
│
├── logs/                      # ログファイル
├── data/                      # SQLite DB
└── systemd/
    ├── temperature-server.service
    └── wifi-monitor.service
```

---

## 4. メモリリーク対策

### 4.1 識別済み問題と対策

| 問題 | 原因 | 対策 |
|------|------|------|
| Selenium メモリ増大 | ブラウザプロセス未終了 | 定期リスタート (1時間) |
| OpenCV フレームバッファ | 参照カウント未リセット | `cv2.destroyAllWindows()` 活用 |
| SQLite コネクション | コネクションプール未管理 | `threading.local()` でスレッド分離 |
| Flask セッション | キャッシュ肥大化 | TTL 設定 + 定期クリア |

### 4.2 監視メカニズム

```python
# memory_monitor.py
- 5分ごと psutil でメモリ使用率チェック
- 閾値超過時 → サービス再起動
- ログに記録 → Web UI で確認可能
```

---

## 5. 実装フェーズ

### **Phase 1: 基盤構築** (1-2日)
- [ ] Raspberry Pi OS セットアップ
- [ ] USB WiFi ドライバインストール
- [ ] Tailscale インストール
- [ ] Python 環境構築
- [ ] 基本 Flask アプリ

### **Phase 2: WiFi 機能** (2-3日)
- [ ] AP 設定 (hostapd + dnsmasq)
- [ ] Station 接続 (Archer T2U Plus)
- [ ] free_wifi_streaming 統合
- [ ] Selenium キャプティブポータル対応

### **Phase 3: データ収集** (1日)
- [ ] ESP32 API エンドポイント
- [ ] SQLite スキーマ
- [ ] データロギング

### **Phase 4: ビデオストリーミング** (1-2日)
- [ ] OpenCV カメラキャプチャ
- [ ] MJPEG エンコード
- [ ] 解像度 3段階設定
- [ ] メモリ最適化

### **Phase 5: UI & 管理** (2日)
- [ ] ダッシュボード HTML/JS
- [ ] 管理画面 (Web UI)
- [ ] CLI ツール
- [ ] 設定ファイル管理

### **Phase 6: テスト & 最適化** (1-2日)
- [ ] メモリリークテスト
- [ ] 24時間連続稼働テスト
- [ ] エラーハンドリング
- [ ] ドキュメント完成

---

## 6. 管理機能 (ワンクリック実行)

### 6.1 Web UI

```
管理画面 (http://192.168.11.57:5000/management)
├─ ステータス表示
│  ├─ WiFi 状態 (AP/Station/Internet)
│  ├─ メモリ使用率
│  ├─ ディスク使用率
│  └─ 最後の ESP32 受信時刻
│
├─ WiFi 設定
│  ├─ AP 有効/無効
│  ├─ Station 再接続
│  ├─ フリーWiFi 監視 ON/OFF
│  └─ ネットワーク再スキャン
│
├─ ビデオストリーミング設定
│  ├─ 解像度選択 (360p/720p/1080p)
│  ├─ FPS 調整
│  └─ 有効/無効
│
├─ システム管理
│  ├─ サービス再起動
│  ├─ ログダウンロード
│  ├─ メモリキャッシュ削除
│  └─ Reboot
│
└─ データ管理
   ├─ DB バックアップ
   ├─ データ削除
   └─ CSV エクスポート
```

### 6.2 CLI ツール

```bash
# 使用例
python3 -m cli.management_cli --status
python3 -m cli.management_cli --wifi-scan
python3 -m cli.management_cli --restart-service wifi_manager
python3 -m cli.management_cli --memory-cleanup
python3 -m cli.management_cli --backup-database
```

---

## 7. 遠隔操作 (Tailscale)

```
外部デバイス
   ↓
Tailscale (100.67.31.61)
   ↓
Raspberry Pi
   ↓
Web UI / SSH / VNC
```

---

## 8. エラーハンドリング & 回復策

| 状況 | 検知方法 | 自動対応 |
|------|----------|----------|
| ESP32 接続断 | 5分間データ無し | アラート表示、ログ記録 |
| WiFi 接続喪失 | ping 失敗 | 再接続試行 (3回) |
| メモリ 80% 超過 | psutil 監視 | キャッシュ削除 → サービス再起動 |
| Selenium クラッシュ | プロセス監視 | 自動再起動 |
| ビデオキャプチャ失敗 | 例外キャッチ | 再初期化 |

---

## 9. 次ステップ

1. **確認事項の回答待ち** ← 現在ここ
2. **ディレクトリ構成の作成**
3. **Phase 1 実装開始**

---

## 質問・確認事項

- [ ] このアーキテクチャで問題ないか？
- [ ] メモリ監視の閾値は？（デフォルト: 80%）
- [ ] ログ保存期間は？（デフォルト: 7日）
- [ ] 他の要件変更はないか？

