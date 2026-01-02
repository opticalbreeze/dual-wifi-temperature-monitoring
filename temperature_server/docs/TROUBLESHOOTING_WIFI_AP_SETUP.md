# WiFi AP セットアップ トラブルシューティング記録

**作成日**: 2025-12-28  
**問題**: ラズパイのWiFi AP（wlan1）が正常に動作しない、温度サーバーのセンサーデータが表示されない

---

## 発生した問題と解決方法

### 1. hostapd設定ファイルの行末コード問題

#### 問題
- `hostapd`サービスが起動しない
- エラーメッセージ: `'ine 3: invalid/unknown driver 'nl80211`
- 設定ファイルが正しく解析されない

#### 原因
- Windows環境で作成した`hostapd.conf`ファイルがWindows形式の行末コード（`\r\n`）を使用していた
- Linuxの`hostapd`はUnix形式の行末コード（`\n`）を要求する

#### 解決方法
```bash
# ラズパイ上で行末コードを変換
cat ~/hostapd.conf | tr -d '\r' | sudo tee /etc/hostapd/hostapd.conf > /dev/null
```

#### 教訓
- **WindowsからLinuxにファイルを転送する際は、行末コードに注意**
- **SCPで転送した設定ファイルは、必ず行末コードを確認・変換する**
- **または、ラズパイ上で直接ファイルを作成する（`tee`や`cat`のヒアドキュメントを使用）**

---

### 2. WiFiドライバーの確認

#### 問題
- `driver=nl80211`が認識されないエラー

#### 原因の確認
- **8821auドライバーはGitHubのオープンソースドライバー（morrownr/8821au-20210708）を使用する必要がある**
- メーカーのドライバーでは動作しない
- `lsmod | grep 8821`でドライバーがロードされていることを確認済み

#### 解決方法
- ドライバー自体は問題なし（行末コードの問題だった）

#### 教訓
- **USB WiFiドングル（TP-Link Archer T2U Plus, RTL8821AU）は、必ずGitHubのオープンソースドライバーを使用**
- **ドライバーのインストール方法は`WIFI_SETUP.md`を参照**

---

### 3. IPアドレスの設定ミス

#### 問題
- `wlan1`のIPアドレスが`192.168.1.93`になっていた（誤り）
- APモードでは`192.168.4.1/24`であるべき

#### 原因
- `dhcpcd`サービスが存在しない環境で、`/etc/dhcpcd.conf`の設定が反映されなかった
- NetworkManagerが管理している可能性

#### 解決方法
```bash
# 手動でIPアドレスを設定
sudo ip addr del 192.168.1.93/24 dev wlan1 2>/dev/null
sudo ip addr add 192.168.4.1/24 dev wlan1
```

#### 重要な注意事項
- **`wlan0`（オンボードWiFi）**: Stationモード → インターネット接続用（192.168.1.x）
- **`wlan1`（USB WiFi）**: APモード → ESP32接続用（192.168.4.1）
- **絶対に`wlan0`のIPアドレスを変更してはいけない**（ネットワークから切断される）

#### 教訓
- **デュアルWiFi構成を理解してから設定する**
- **IPアドレス設定前に、どのインターフェースを設定するか必ず確認**
- **`dhcpcd`サービスがない環境では、手動設定またはNetworkManagerの設定が必要**

---

### 4. ポート5000の競合問題（繰り返し発生）

#### 問題
- `Address already in use`エラーが繰り返し発生
- サーバー起動のたびに同じエラーチェックを実行してしまう

#### 原因
- サーバーが既に起動しているのに、それを確認せずに起動コマンドを実行
- ポートを使用しているプロセスを特定する前に、同じ手法で検証を繰り返した

#### 解決方法
```bash
# ポート5000を使用しているプロセスを直接特定
sudo lsof -i :5000
# または
sudo ss -tlnp | grep :5000
# または
sudo fuser 5000/tcp
```

#### 教訓
- **サーバー起動前に、必ずポートの使用状況を確認する**
- **同じエラーが発生した場合、以前と同じ手法で検証しない（別の方法を試す）**
- **プロセスが既に起動している場合は、そのまま使用するか、明示的に停止してから再起動する**

---

### 5. コマンド実行のレスポンス待ち問題

#### 問題
- SSHコマンドを実行しても結果が返ってこない（「レス無し」「反応なし」）
- タイムアウトが発生する

#### 原因
- ネットワークの遅延
- コマンドが長時間実行されている（フロントエンドプロセスになっている）
- バックグラウンドプロセスとして実行すべきところをフォアグラウンドで実行

#### 解決方法
- バックグラウンドで実行する場合は`nohup`と`&`を使用
- または、`systemd`サービスとして管理
- 短時間で結果が返るコマンドのみを実行

#### 教訓
- **長時間実行されるコマンドは、バックグラウンド実行（`&`）または`systemd`サービスを使用**
- **SSH経由でのコマンド実行は、できるだけ短時間で完了するものにする**
- **結果が返らない場合は、別の方法で確認する**

---

### 6. 温度サーバーの起動確認

#### 問題
- 再起動後に温度サーバーが起動していない
- ブラウザでセンサーデータが表示されない

#### 解決方法
```bash
# サーバーを起動
cd ~/temperature_monitoring/temperature_server
source venv/bin/activate
nohup python run.py > server.log 2>&1 &

# またはsystemdサービスとして設定（推奨）
```

#### 推奨事項
- **再起動後も自動起動するように、`systemd`サービスとして設定する**
- **サービスファイルの場所**: `temperature_server/systemd/temperature-server.service`

---

## チェックリスト（今後同じ問題を避けるため）

### WiFi AP設定時
- [ ] `hostapd.conf`の行末コードをUnix形式（`\n`）に変換
- [ ] `wlan1`のIPアドレスが`192.168.4.1/24`であることを確認
- [ ] `wlan0`のIPアドレスは変更しない
- [ ] `8821au`ドライバーが正しくロードされていることを確認（`lsmod | grep 8821`）
- [ ] `hostapd`サービスが正常に起動していることを確認（`sudo systemctl status hostapd`）
- [ ] `dnsmasq`サービスが正常に起動していることを確認（`sudo systemctl status dnsmasq`）

### サーバー起動時
- [ ] ポート5000を使用しているプロセスを確認（`sudo lsof -i :5000`）
- [ ] 既にサーバーが起動している場合は、そのまま使用するか明示的に停止
- [ ] 同じエラーが発生した場合、以前と同じ手法で検証しない

### ファイル転送時
- [ ] WindowsからLinuxへの転送時は、行末コードに注意
- [ ] 設定ファイルは、可能な限りラズパイ上で直接作成する
- [ ] 転送後は、ファイルの内容と権限を確認

---

## 正しい手順まとめ

### WiFi AP セットアップ（新規環境）

1. **ドライバーインストール確認**
   ```bash
   lsmod | grep 8821  # ドライバーがロードされているか確認
   ```

2. **hostapd設定ファイル作成（ラズパイ上で直接作成）**
   ```bash
   sudo tee /etc/hostapd/hostapd.conf > /dev/null << 'EOF'
   interface=wlan1
   driver=nl80211
   ssid=RaspberryPi_Temperature
   hw_mode=g
   channel=6
   wmm_enabled=1
   macaddr_acl=0
   auth_algs=1
   ignore_broadcast_ssid=0
   wpa=2
   wpa_passphrase=RaspberryPi2025
   wpa_key_mgmt=WPA-PSK
   wpa_pairwise=CCMP
   wpa_ptk_rekey=600
   EOF
   ```

3. **IPアドレス設定**
   ```bash
   # wlan1のIPアドレスを設定
   sudo ip addr add 192.168.4.1/24 dev wlan1
   ```

4. **サービス起動確認**
   ```bash
   sudo systemctl start hostapd
   sudo systemctl status hostapd
   sudo systemctl status dnsmasq
   ```

5. **動作確認**
   ```bash
   ip addr show wlan1  # IPアドレス確認
   sudo hostapd_cli -i wlan1 status  # AP状態確認（オプション）
   ```

### 温度サーバー起動

1. **ポート確認**
   ```bash
   sudo lsof -i :5000
   ```

2. **サーバー起動（既に起動している場合はスキップ）**
   ```bash
   cd ~/temperature_monitoring/temperature_server
   source venv/bin/activate
   nohup python run.py > server.log 2>&1 &
   ```

3. **動作確認**
   ```bash
   tail -f logs/app.log  # ログ確認
   curl http://localhost:5000/api/status  # API確認
   ```

---

## 参考ドキュメント

- `temperature_server/docs/WIFI_SETUP.md`: WiFi APセットアップの詳細手順
- `temperature_server/docs/TROUBLESHOOTING.md`: 一般的なトラブルシューティング
- `temperature_server/systemd/temperature-server.service`: systemdサービス設定例





