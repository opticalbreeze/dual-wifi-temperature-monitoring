# WiFi接続問題の診断方法

## 状況の整理

**TeraTerm（SSH）で接続できている = WiFi接続は正常**

MACアドレスフィルターで締め出されている場合は、WiFi接続自体ができないため、SSH接続も不可能です。

## 考えられる問題

### 1. インターネット接続の問題
- WiFiには接続できているが、インターネットにアクセスできない
- キャプティブポータルの認証が通らない

### 2. free_wifiプログラムの問題
- 自動認証が動作していない
- キャプティブポータルの処理が失敗している

### 3. 特定のサービスだけが接続できない
- 一部のWebサイトやサービスにアクセスできない
- DNSの問題

## 診断コマンド

### 1. インターネット接続の確認

```bash
echo "=== インターネット接続テスト ===" && \
echo "1. Google DNSへのping" && \
ping -c 3 8.8.8.8 && \
echo "" && \
echo "2. ドメイン名解決テスト" && \
nslookup google.com && \
echo "" && \
echo "3. HTTP接続テスト" && \
curl -I --max-time 5 http://example.com 2>&1 | head -5
```

### 2. free_wifiプログラムの状態確認

```bash
echo "=== free_wifiプログラムの状態 ===" && \
echo "1. サービス状態" && \
systemctl status guest2-repeater.service --no-pager | head -15 && \
echo "" && \
echo "2. 最近のログ" && \
journalctl -u guest2-repeater.service --since "1 hour ago" | tail -30
```

### 3. キャプティブポータルの確認

```bash
echo "=== キャプティブポータル確認 ===" && \
echo "1. 認証ページへのアクセス" && \
curl -L --max-time 10 http://example.com 2>&1 | grep -i -E "login|auth|portal|guest" | head -5 && \
echo "" && \
echo "2. リダイレクト確認" && \
curl -I --max-time 10 http://example.com 2>&1 | grep -i -E "location|302|301"
```

### 4. ネットワークルーティングの確認

```bash
echo "=== ネットワークルーティング ===" && \
echo "1. デフォルトゲートウェイ" && \
ip route show default && \
echo "" && \
echo "2. DNS設定" && \
cat /etc/resolv.conf && \
echo "" && \
echo "3. ルーティングテーブル" && \
ip route show
```

## 問題の特定方法

### パターン1: インターネットに全く接続できない

**症状:**
- `ping 8.8.8.8` が失敗
- `curl http://example.com` がタイムアウト

**原因:**
- キャプティブポータルの認証が必要
- free_wifiプログラムが動作していない可能性

**対処:**
```bash
# free_wifiプログラムを再起動
sudo systemctl restart guest2-repeater.service

# 手動で再接続を試行
# GUIアプリケーションで「再接続」ボタンをクリック
```

### パターン2: IPアドレスは取得できるが、インターネットに接続できない

**症状:**
- `ping 8.8.8.8` が成功
- `curl http://example.com` がタイムアウト
- DNS解決が失敗

**原因:**
- DNS設定の問題
- ファイアウォールの問題

**対処:**
```bash
# DNS設定を確認・変更
sudo nmcli connection modify "接続名" ipv4.dns "8.8.8.8 8.8.4.4"
sudo systemctl restart NetworkManager
```

### パターン3: 特定のサービスだけ接続できない

**症状:**
- 一部のWebサイトにアクセスできない
- 特定のポートがブロックされている

**原因:**
- プロバイダーの制限
- ポートフィルタリング

## 一括診断コマンド

```bash
echo "=========================================" && \
echo "WiFi接続問題の一括診断" && \
echo "=========================================" && \
echo "" && \
echo "【1. 基本接続確認】" && \
ip addr show wlan0 | grep "inet " && \
echo "" && \
echo "【2. インターネット接続】" && \
ping -c 2 8.8.8.8 2>&1 | tail -3 && \
echo "" && \
echo "【3. DNS解決】" && \
nslookup google.com 2>&1 | grep -A2 "Name:" && \
echo "" && \
echo "【4. HTTP接続】" && \
curl -I --max-time 5 http://example.com 2>&1 | head -3 && \
echo "" && \
echo "【5. free_wifiプログラム状態】" && \
systemctl is-active guest2-repeater.service && \
echo "" && \
echo "【6. 最近のエラー】" && \
journalctl -u guest2-repeater.service --since "1 hour ago" | grep -i error | tail -5 && \
echo "" && \
echo "========================================="
```

