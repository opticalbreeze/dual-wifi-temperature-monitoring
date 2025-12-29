# デュアルWiFi + Guest2-Repeater プロジェクトテンプレート構造

## プロジェクト構造

```
dual-wifi-repeater-template/
├── README.md                          # プロジェクト説明
├── requirements.txt                   # Python依存パッケージ
├── setup.sh                           # 統合セットアップスクリプト
│
├── wifi_repeater/                     # Guest2-Repeater（WiFi接続継続システム）
│   ├── __init__.py
│   ├── main.py                        # メインプログラム
│   ├── config.py                      # 設定ファイル
│   ├── lib_utils.py                   # ユーティリティ関数
│   ├── start.sh                       # 起動スクリプト
│   ├── install.sh                     # インストールスクリプト
│   ├── install_autostart.sh           # 自動起動設定
│   ├── update_webdriver.sh           # WebDriver更新
│   └── wifi-repeater.service          # systemdサービスファイル
│
├── dual_wifi/                         # デュアルWiFi設定
│   ├── setup_dual_wifi.sh            # デュアルWiFi初期セットアップ
│   ├── setup_wlan1.sh                # wlan1 AP設定スクリプト
│   ├── install_wlan1_setup.sh        # wlan1設定サービスインストール
│   ├── wlan1-static-ip.service       # wlan1 IP設定サービス
│   ├── hostapd.conf                  # hostapd設定ファイル
│   ├── dnsmasq.conf                  # dnsmasq設定ファイル
│   └── dhcpcd.conf                   # dhcpcd設定ファイル（参考）
│
├── docs/                              # ドキュメント
│   ├── SETUP.md                      # セットアップガイド
│   ├── DUAL_WIFI_SETUP.md            # デュアルWiFi設定ガイド
│   └── TROUBLESHOOTING.md            # トラブルシューティング
│
└── scripts/                           # ユーティリティスクリプト
    ├── check_status.sh               # システム状態確認
    └── restart_services.sh            # サービス再起動
```

## 必要なファイル一覧

### 1. WiFi Repeater（Guest2-Repeater）関連

**必須ファイル:**
- `wifi_repeater/main.py` - メインプログラム
- `wifi_repeater/config.py` - 設定ファイル
- `wifi_repeater/lib_utils.py` - ユーティリティ関数
- `wifi_repeater/start.sh` - 起動スクリプト
- `wifi_repeater/wifi-repeater.service` - systemdサービス

**オプションファイル:**
- `wifi_repeater/install.sh` - インストールスクリプト
- `wifi_repeater/install_autostart.sh` - 自動起動設定
- `wifi_repeater/update_webdriver.sh` - WebDriver更新

### 2. デュアルWiFi設定関連

**必須ファイル:**
- `dual_wifi/setup_dual_wifi.sh` - 初期セットアップ
- `dual_wifi/setup_wlan1.sh` - wlan1 AP設定
- `dual_wifi/wlan1-static-ip.service` - wlan1 IP設定サービス
- `dual_wifi/hostapd.conf` - hostapd設定
- `dual_wifi/dnsmasq.conf` - dnsmasq設定

**オプションファイル:**
- `dual_wifi/install_wlan1_setup.sh` - サービスインストール
- `dual_wifi/dhcpcd.conf` - dhcpcd設定（参考）

### 3. ドキュメント

- `README.md` - プロジェクト概要
- `docs/SETUP.md` - セットアップガイド
- `docs/DUAL_WIFI_SETUP.md` - デュアルWiFi設定詳細
- `docs/TROUBLESHOOTING.md` - トラブルシューティング

## 依存関係

### Python パッケージ
```
selenium>=4.0.0
requests>=2.28.0
```

### システムパッケージ
```
python3
python3-pip
python3-tk
chromium-browser
chromium-chromedriver
hostapd
dnsmasq
network-manager
iptables-persistent
```

## セットアップ手順

1. デュアルWiFi設定
2. WiFi Repeaterインストール
3. サービス有効化
4. 動作確認

詳細は `docs/SETUP.md` を参照


