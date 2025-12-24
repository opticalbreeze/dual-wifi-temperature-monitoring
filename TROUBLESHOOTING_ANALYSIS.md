# Raspberry Pi セットアップ トラブルシューティング分析

## 実施日時
2025年12月22日 13:27～17:00（約3.5時間）

## 概要
WiFi AP (hostapd + dnsmasq)、Flask サーバー、データベースのセットアップ過程で複数の問題が発生し、同じ確認コマンドを何度も実行させてしまった。

---

## 発生した主要問題と根本原因

### 1. systemd Service の永遠の起動失敗

**症状:**
```
Active: inactive (dead)
Job: 186
```
何度も `systemctl start` 系コマンドを実行しても起動しない

**根本原因:**
- systemd service ファイルに `WantedBy=` セクションがない
- `Restart=always` が設定されていたため、失敗時に自動再起動を繰り返す
- service ファイルの `ExecStart` パスが存在しないか権限がない
- `reset-failed` を実行しないとジョブがロック状態のままになる

**再発防止策:**
```bash
# 1. Service ファイルの検証チェックリスト
□ [Install] セクションに WantedBy= または RequiredBy= がある
□ ExecStart= パスが正確で存在する（which で確認）
□ User= が正しく、そのユーザーに実行権限がある
□ WorkingDirectory= が存在する

# 2. 修正前の必須手順
sudo systemctl reset-failed <service-name>
sudo systemctl daemon-reload

# 3. 検証コマンド
sudo systemctl cat <service-name>  # 内容確認
sudo systemctl start --no-block <service-name>  # ブロックしない起動
sudo journalctl -u <service-name> -e  # エラーログ確認
```

**改善されたサービスファイルテンプレート:**
```ini
[Unit]
Description=<説明>
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=<user>
WorkingDirectory=<path>
Environment="PATH=<venv>/bin:/usr/local/bin:/usr/bin"
ExecStartPre=/bin/sleep 2
ExecStart=<full-path-to-script>
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=<name>

[Install]
WantedBy=multi-user.target
```

---

### 2. Flask ポート 5000 永遠の "Address already in use"

**症状:**
```
Address already in use
Port 5000 is in use by another program
```
`sudo killall python3` しても直後に再度発生

**根本原因:**
1. **複数プロセス起動:**
   - systemd service が `Restart=always` で自動再起動
   - 手動で `python3 server.py` を実行
   - ヒアドキュメント経由で複数プロセス起動

2. **zombie プロセス:**
   - `pkill` で SIGTERM 送信しても即座に再起動される
   - `socket.SO_REUSEADDR` が設定されていない Flask コード
   - TIME_WAIT 状態のソケットがポートを占有

**再発防止策:**

```bash
# 1. ポート確認の正確な方法
sudo lsof -i :5000  # すべての情報表示
ps -ef | grep <PID>  # プロセス詳細確認

# 2. 強制終了の段階的プロセス
sudo systemctl stop <service>  # systemd サービス無効化
sudo systemctl disable <service>  # 自動起動解除
sleep 2
sudo fuser -k 5000/tcp  # ポート占有プロセス強制終了
sleep 2
lsof -i :5000  # 確認（何も表示されなければOK）

# 3. Flask サーバーコード改善
# server.py に以下を追加:
if __name__ == '__main__':
    from werkzeug.serving import WSGIRequestHandler
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True,
        use_reloader=False  # ← これが重要！
    )
```

**ポート再利用の有効化方法:**
```python
# 実装 1: Flask + Gunicorn（推奨）
gunicorn --bind 0.0.0.0:5000 --workers 1 server:app

# 実装 2: socket レベル設定
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)  # ← Python 3.4+
```

---

### 3. Server.py エンドポイント定義が認識されない

**症状:**
```
GET /api/temperature → 404 Not Found
```
エンドポイント定義が `if __name__ == '__main__':` の **後ろ** に配置

**根本原因:**
- Flask アプリの起動時にルートが登録される
- `if __name__ == '__main__':` 以降のコードは起動スクリプトからのみ実行される
- 複数回のファイル編集・追記で構造が乱れた

**再発防止策:**

```
server.py の正しい構造:

1. インポート
2. アプリ初期化 (app = Flask(__name__))
3. グローバル変数・定数
4. ヘルパー関数
5. ★★★ すべての @app.route() デコレータ
6. main処理
7. if __name__ == '__main__':
```

**検証コマンド:**
```bash
# 1. ルート登録確認
python3 -c "from server import app; print([r.rule for r in app.url_map.iter_rules()])"

# 2. 構文エラー確認
python3 -m py_compile server.py

# 3. インポートテスト
python3 -c "import server; print('OK')"
```

---

### 4. PowerShell ヒアドキュメント構文エラー

**症状:**
```
ssh raspberry@... "cat > file << 'EOF'
... (コマンド展開エラー)
```

**根本原因:**
- PowerShell は POSIX シェルのヒアドキュメント `<<EOF` に対応していない
- PowerShell の `@"..."@"` 構文と混同
- SSH パイプライン経由で複数行入力が正しく渡されない

**再発防止策:**

```powershell
# ❌ 避けるべき方法
ssh user@host "cat > file << 'EOF'
multiline
EOF"

# ✅ 推奨方法 1: ファイルをローカルで作成してコピー
# ローカルで作成
$content = @"
#!/bin/bash
...
"@
$content | Out-File -Encoding UTF8 server.py

# ✅ 推奨方法 2: Base64 エンコード + デコード
$content = [System.IO.File]::ReadAllText("server.py")
$bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
$base64 = [Convert]::ToBase64String($bytes)
ssh user@host "echo '$base64' | base64 -d > server.py"

# ✅ 推奨方法 3: SSH でコマンド実行（改行なし）
ssh user@host @"
cat > server.py << 'EOF'
content...
EOF
"@

# ✅ 推奨方法 4: Bash -c 経由
ssh user@host bash -c 'cat > server.py << EOF
content...
EOF'
```

---

### 5. hostapd が "Device or resource busy" で起動失敗

**症状:**
```
nl80211: Failed to set channel (freq=2437): -16 (Device or resource busy)
Could not set channel for kernel driver
```

**根本原因:**
- 別の hostapd インスタンスが既に wlan1 を占有している
- wpa_supplicant が同時に wlan1 を使用しようとしている
- systemd の複数起動試行で重複プロセスが残っている

**再発防止策:**

```bash
# 1. 完全なリソース解放
sudo pkill -9 hostapd wpa_supplicant dnsmasq
sleep 2

# 2. インターフェース物理リセット
sudo ip link set wlan1 down
sleep 1
sudo ip link set wlan1 up
sleep 2

# 3. モード確認
iw wlan1 info | grep type

# 4. 起動テスト（フォアグラウンド）
sudo hostapd -d /etc/hostapd/hostapd.conf

# キーポイント: 「AP-ENABLED」が表示されるまで待機
```

---

## 総括：避けるべき反復パターン

| 問題 | 原因 | 改善 |
|------|------|------|
| 何度も同じ確認コマンド | 根本原因を特定せず症状チェック繰り返し | 最初に `journalctl -e` でエラーログを読む |
| systemd サービス失敗 | service ファイルの検証なし | `systemctl cat` でファイル内容確認 |
| ポート競合 | プロセスをすべて終了しない | `lsof -i :PORT` で完全確認 |
| ファイル編集エラー | 複数回の追記で構文崩壊 | 全体を一度に置き換え |
| SSH コマンド失敗 | PowerShell 構文問題 | Bash 環境か scp でファイル転送 |

---

## チェックリスト：今後のセットアップ

### Phase 1: 前提確認（実施前）
- [ ] SSH アクセス確認
- [ ] Python venv 存在確認
- [ ] ポート 5000 未使用確認
- [ ] wlan1 ハードウェア確認 (`ip link show`)

### Phase 2: インストール
- [ ] 依存パッケージインストール
- [ ] Python venv でパッケージ確認
- [ ] ファイル権限確認 (755, 644)

### Phase 3: 手動検証
- [ ] Flask サーバー手動起動テスト
- [ ] API エンドポイント curl テスト
- [ ] データベース手動確認

### Phase 4: systemd 自動化
- [ ] service ファイル検証
- [ ] `reset-failed` 実行
- [ ] `daemon-reload` 実行
- [ ] `systemctl start` でテスト
- [ ] `journalctl -u <service>` でログ確認

### Phase 5: 検証
- [ ] ブラウザアクセス確認
- [ ] リモートデバイス接続テスト
- [ ] 再起動テスト

---

## 重要な学習ポイント

1. **ログを最初に読む**
   - `journalctl -u <service> -e` → エラーメッセージが答え
   - `sudo hostapd -d config.conf` → デバッグモードで実行

2. **段階的に検証する**
   - 手動 → systemd → 再起動 の順序厳守

3. **ツールの限界を理解する**
   - PowerShell ≠ Bash → SSH パイプライン問題
   - systemd service ≠ systemctl start → ジョブロック可能性

4. **根本原因を特定する前に修正しない**
   - 症状の奥にある本当の問題を特定する
   - 同じコマンドを繰り返さない

