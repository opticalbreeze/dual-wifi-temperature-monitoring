# 🌐 デュアル WiFi セットアップガイド

**最重要ドキュメント：このセットアップが本プロジェクトの核となります**

---

## 概要

Raspberry Pi 4 で **2つの独立した WiFi ネットワーク** を実現します：

- **wlan0** (オンボード WiFi)：Station モード → インターネット接続
- **wlan1** (USB WiFi ドングル)：AP モード → ESP32 接続用アクセスポイント

---

## 必要なハードウェア

### 1. USB WiFi ドングル

**推奨：TP-Link Archer T2U Plus**

```bash
# USB デバイス ID: 2357:0120
# チップセット: Realtek RTL8821AU
# 周波数: 2.4GHz / 5GHz (デュアルバンド)
# 認定: FCC, CE

# 購入時の確認
lsusb | grep "2357:0120"
```

**なぜこれを選ぶのか？**
- Raspberry Pi で確認済みの動作実績
- オープンソースドライバ利用可能
- 5GHz 帯域対応で干渉回避可能
- 価格がリーズナブル

---

## Step 1: USB WiFi ドングルドライバのインストール

### 1.1 システムアップデート

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y build-essential dkms
```

### 1.2 RTL8821AU ドライバのインストール

```bash
# ドライバソースのダウンロード
cd /tmp
git clone https://github.com/morrownr/8821au-20210708.git
cd 8821au-20210708

# インストール
sudo ./install-driver.sh

# 再起動
sudo reboot
```

### 1.3 インストール確認

```bash
# ドングルが認識されているか確認
lsusb | grep -i "tp-link\|realtek"

# 出力例：
# Bus 001 Device 004: ID 2357:0120 TP-Link

# インターフェースが表示されているか確認
ip link show

# 出力例：
# 4: wlan1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500
#    link/ether 74:fe:ce:c8:4d:57 brd ff:ff:ff:ff:ff:ff
```

---

## Step 2: WiFi 設定ファイルの準備

### 2.1 dhcpcd 設定

```bash
sudo nano /etc/dhcpcd.conf
```

以下を **ファイルの末尾** に追加：

```bash
# wlan1 (USB WiFi) を静的 IP で設定
interface wlan1
static ip_address=192.168.4.1/24
nohook wpa_supplicant
```

**説明：**
- `static ip_address=192.168.4.1/24`：AP 用の固定 IP
- `nohook wpa_supplicant`：hostapd が管理するため wpa_supplicant を無効化

### 2.2 hostapd 設定

```bash
sudo nano /etc/hostapd/hostapd.conf
```

以下の内容で作成（既存の場合は置き換え）：

```ini
# ===== Basic Settings =====
interface=wlan1
driver=nl80211
ssid=RaspberryPi_Temperature
hw_mode=g
channel=6

# ===== Security Settings =====
wpa=2
wpa_passphrase=RaspberryPi2025
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
wpa_group_rekey=86400

# ===== Other Settings =====
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
```

**設定の意味：**

| 項目 | 値 | 説明 |
|------|-----|------|
| interface | wlan1 | USB WiFi インターフェース |
| driver | nl80211 | Linux nl80211 ドライバ |
| ssid | RaspberryPi_Temperature | SSID (ネットワーク名) |
| hw_mode | g | 802.11g (2.4GHz) |
| channel | 6 | チャンネル 6 (干渉が少ない) |
| wpa | 2 | WPA2 暗号化 |
| wpa_passphrase | RaspberryPi2025 | WiFi パスワード |
| wpa_key_mgmt | WPA-PSK | PSK 認証方式 |
| wpa_pairwise | CCMP | CCMP 暗号化プロトコル |

**チャンネル選択の理由：**
```
2.4GHz WiFi チャンネル配置
Ch 1  (2412 MHz) ━━━━━━━  推奨 ✓
Ch 6  (2437 MHz) ━━━━━━━  推奨 ✓ ← このシステムで使用
Ch 11 (2462 MHz) ━━━━━━━  推奨 ✓
```

### 2.3 dnsmasq 設定

```bash
sudo nano /etc/dnsmasq.conf
```

以下を **ファイルの末尾** に追加（既存の dnsmasq 設定がある場合は確認）：

```ini
# wlan1 用 DHCP 設定
interface=wlan1
dhcp-range=192.168.4.2,192.168.4.254,255.255.255.0,24h
server=8.8.8.8
server=8.8.4.4
```

**DHCP レンジの説明：**
```
192.168.4.0/24 ネットワーク
├─ 192.168.4.1      Raspberry Pi (AP)
├─ 192.168.4.2-254  クライアント用 (DHCP レンジ)
│  ├─ 192.168.4.185  ESP32_01 (例)
│  ├─ 192.168.4.186  ESP32_02 (例)
│  └─ ...
└─ 192.168.4.255    ブロードキャストアドレス
```

---

## Step 3: iptables (ファイアウォール) 設定

### 3.1 iptables ルール追加

```bash
# AP (wlan1) から Station (wlan0) へのトラフィック許可
sudo iptables -A FORWARD \
  -i wlan1 -o wlan0 -j ACCEPT

# Station (wlan0) からの応答トラフィック許可
sudo iptables -A FORWARD \
  -i wlan0 -o wlan1 \
  -m state --state RELATED,ESTABLISHED -j ACCEPT

# NAT 設定 (アドレス変換)
sudo iptables -t nat \
  -A POSTROUTING -o wlan0 -j MASQUERADE
```

### 3.2 iptables ルールの永続化

```bash
# iptables-persistent をインストール
sudo apt-get install -y iptables-persistent

# 現在のルールを保存
sudo iptables-save | sudo tee /etc/iptables/rules.v4

# 確認
sudo iptables -L -n -v
```

**iptables ルールの説明：**

```
┌─────────────────────────────────────────────────┐
│ Rule 1: FORWARD -i wlan1 -o wlan0 -j ACCEPT    │
│ ↓                                               │
│ ESP32 (wlan1) → Raspberry Pi (wlan0)            │
│ → インターネット へのトラフィック許可           │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Rule 2: FORWARD -i wlan0 -o wlan1 -j ACCEPT    │
│ (RELATED, ESTABLISHED state only)               │
│ ↓                                               │
│ インターネット → Raspberry Pi (wlan0)           │
│ → ESP32 (wlan1) への応答トラフィック許可       │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Rule 3: NAT -o wlan0 -j MASQUERADE             │
│ ↓                                               │
│ wlan0 から送信するパケットのソース IP を      │
│ Raspberry Pi (192.168.11.57) に変換            │
└─────────────────────────────────────────────────┘

結果：
  192.168.4.185 (ESP32) 
    → パケットのソース IP を 192.168.11.57 に変換
    → インターネット上から見ると Raspberry Pi からの要求に見える
```

---

## Step 4: サービス設定

### 4.1 hostapd サービス有効化

```bash
# hostapd が systemd で自動起動されるよう設定
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl start hostapd

# 確認
sudo systemctl status hostapd
```

### 4.2 dnsmasq サービス有効化

```bash
sudo systemctl enable dnsmasq
sudo systemctl start dnsmasq

# 確認
sudo systemctl status dnsmasq
```

---

## Step 5: 接続テスト

### 5.1 Raspberry Pi 側でのテスト

```bash
# wlan1 が UP しているか確認
ip addr show wlan1
# 出力例：
# 4: wlan1: <BROADCAST,MULTICAST,UP,LOWER_UP>
#    inet 192.168.4.1/24 scope global wlan1

# AP が正常に動作しているか確認
sudo hostapd_cli status
# 出力例：
# State=ENABLED
# Num STA=0 (接続クライアント数)

# DHCP が正常に動作しているか確認
sudo systemctl status dnsmasq
```

### 5.2 別のデバイスでの接続テスト

別の PC やスマートフォンから以下を確認：

```
1. WiFi ネットワーク一覧で「RaspberryPi_Temperature」が表示
2. パスワード「RaspberryPi2025」で接続可能
3. IP アドレスが 192.168.4.x range で割り当てられる
4. Raspberry Pi (192.168.4.1) に ping 応答がある
   ping 192.168.4.1
```

---

## Step 6: ESP32 からの接続確認

### 6.1 ESP32 WiFi コード例

```cpp
#include <WiFi.h>

const char* ssid = "RaspberryPi_Temperature";
const char* password = "RaspberryPi2025";

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  WiFi.begin(ssid, password);
  
  int timeout = 0;
  while (WiFi.status() != WL_CONNECTED && timeout < 20) {
    delay(500);
    Serial.print(".");
    timeout++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ Connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n✗ Failed to connect");
  }
}

void loop() {
  // メイン処理
}
```

### 6.2 接続確認

```bash
# Raspberry Pi で接続しているクライアントを確認
sudo iw dev wlan1 station dump

# 出力例：
# Station 9c:9e:6e:f7:28:2c (on wlan1)
#   inactive time:  100 ms
#   rx bytes:       1234
#   rx packets:     23
#   tx bytes:       5678
#   tx packets:     45
#   signal:         -45 dBm
```

---

## Step 7: Flask サーバーの設定確認

### 7.1 Flask が全インターフェースでリッスンしているか確認

```bash
# config.py で FLASK_HOST = '0.0.0.0' が設定されていることを確認
grep "FLASK_HOST" ~/temperature_server/config.py

# サーバーがリッスンしているポートを確認
sudo netstat -tlnp | grep 5000
# または
sudo ss -tlnp | grep 5000

# 出力例：
# tcp  0  0  0.0.0.0:5000  0.0.0.0:*  LISTEN  12345/python3
```

### 7.2 ネットワークテスト

```bash
# ローカルホストテスト (成功すれば Flask は動作している)
curl -X POST http://127.0.0.1:5000/api/temperature \
  -H "Content-Type: application/json" \
  -d '{"device_id":"TEST","name":"test","location":"test","temperature":25.0}'

# 192.168.4.1 テスト (ネットワーク経由の確認)
curl -X POST http://192.168.4.1:5000/api/temperature \
  -H "Content-Type: application/json" \
  -d '{"device_id":"TEST","name":"test","location":"test","temperature":25.0}'

# 両方で 201 Created が返ればOK
```

---

## トラブルシューティング（初期段階）

### 問題：wlan1 が見つからない

```bash
# 確認
ip link show | grep wlan1

# 解決：ドライバが正しくインストールされているか確認
dkms status
# 出力例：
# 8821au, 20210708, 6.1.0-13-generic-arm64, arm64: installed

# インストールされていない場合は Step 1 を再実行
```

### 問題：hostapd が起動しない

```bash
# エラーログを確認
sudo journalctl -u hostapd -n 20 --no-pager

# 一般的な原因：
# - wlan1 が UP していない → ip link set wlan1 up
# - /etc/hostapd/hostapd.conf が見つからない
# - 設定ファイルに構文エラーがある
```

### 問題：DHCP が割り当てられない

```bash
# dnsmasq ログ確認
sudo journalctl -u dnsmasq -n 20 --no-pager

# 一般的な原因：
# - dnsmasq が起動していない
# - dhcp-range が設定されていない
# - 別の DHCP サーバーと競合している
```

---

## 高度な設定

### 1. チャンネルの変更（干渉回避）

```bash
# 現在のチャンネルで干渉がないか確認
sudo iw dev wlan0 scan | grep -E "freq|signal strength"

# 干渉がある場合は hostapd.conf でチャンネルを変更
# channel=1    (2412 MHz)
# channel=6    (2437 MHz) ← 推奨
# channel=11   (2462 MHz)
```

### 2. 送信電力の調整

```bash
# 現在の送信電力確認
iw reg get

# 送信電力を上げる（干渉低減）
sudo iw reg set JP  # 国コード設定
```

### 3. 802.11n サポートの有効化

```bash
# hostapd.conf に追加
ieee80211n=1
ht_capab=[SHORT-GI-20][SHORT-GI-40][TX-STBC][RX-STBC1][MAX-AMSDU-7935]
```

---

## ⚠️ よくある失敗パターン

### 1️⃣ iptables ルールが設定されていない

**症状：** ESP32 は AP に接続できるが、インターネットにアクセスできない

**原因：** NAT ルールが設定されていない

**解決：**
```bash
sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

### 2️⃣ Flask が localhost でのみリッスン

**症状：** localhost テストは成功するが、192.168.4.1 テストが失敗

**原因：** config.py で `FLASK_HOST = '127.0.0.1'` が設定されている

**解決：**
```python
# config.py
FLASK_HOST = '0.0.0.0'  # すべてのインターフェース
```

### 3️⃣ `iw` コマンドのパス問題

**症状：** health check で `Failed to get network info: [Errno 2]`

**原因：** systemd サービスの PATH が限定されているため、`iw` コマンドが見つからない

**解決：**
```python
# wifi_manager.py
subprocess.run(['/usr/sbin/iw', ...])  # フルパスを指定
```

---

## 検証チェックリスト

```
セットアップが完了したか確認：

□ USB WiFi ドングルが認識されている
  lsusb | grep "2357:0120"

□ wlan1 がリッスンしている
  ip addr show wlan1 | grep "inet 192.168.4"

□ hostapd が起動している
  sudo systemctl is-active hostapd

□ dnsmasq が起動している
  sudo systemctl is-active dnsmasq

□ iptables ルールが設定されている
  sudo iptables -L -n | grep "wlan"

□ Flask が 0.0.0.0:5000 でリッスン
  sudo netstat -tlnp | grep 5000

□ localhost テストが成功
  curl http://127.0.0.1:5000/api/status

□ 192.168.4.1 テストが成功
  curl http://192.168.4.1:5000/api/status

□ ESP32 が AP に接続
  sudo iw dev wlan1 station dump

□ Web UI にアクセス可能
  http://192.168.11.57:5000/
```

---

**最後に更新**: 2025年12月24日
