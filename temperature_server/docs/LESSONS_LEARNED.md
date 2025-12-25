# 📚 開発過程で学んだ教訓・失敗から得た知見

**このドキュメントは、6時間以上の試行錯誤から得られた最重要な学習内容です。**

---

## 序論

> 「システムが動かない」という問題は、実は「完全に動かない」のではなく、
> 「どこかの1つの部分が正常に動作していない」ことがほとんどです。
> その部分を見つけるための方法論が本章です。

本プロジェクトの開発過程：
- **開始時刻**: 15:00
- **成功時刻**: 21:18 (6時間 18 分)
- **主要な問題**: 20分間のデータ受信ゼロ
- **最終原因**: 1行の修正（`iw` コマンドのフルパス指定）

---

## 🎯 教訓 1: 「症状」と「原因」の区別

### ❌ 失敗パターン

最初の問題分析：
```
症状：ESP32 がデータを送信できない（error -11）
↓
仮説 1：WiFi AP が動作していない
仮説 2：Flask サーバーが起動していない
仮説 3：ネットワーク設定が間違っている
↓
対応：ドライバを再インストール、設定を何度も変更
```

**結果：** 6 時間の試行錯誤でも解決しない 😤

### ✅ 成功パターン

別のアプローチ（このセッション）：
```
症状：ESP32 がデータを送信できない（error -11）
↓
実際に検証：
1. curl localhost:5000 → 成功 ✓
2. curl 192.168.4.1:5000 → 成功 ✓
3. ping 192.168.4.185 → 成功 ✓
4. hostapd ログで接続確認 → 成功 ✓
5. Flask ログで POST リクエスト確認 → ✓
↓
結論：「システムは完全に正常に動作している」
問題：「バックグラウンドタスクの health check が誤った判定」
↓
修正：subprocess.run(['iw']) → subprocess.run(['/usr/sbin/iw'])
```

**結果：** 数分で解決 ✓

---

## 💡 教訓 2: 段階的検証 (Divide and Conquer)

### マインドセット

複雑なシステムの問題は、**単純な部分から検証する**：

```
【検証の階層】

1. 最下層：ハードウェア認識
   lsusb, ip link show
   
2. ネットワーク層：インターフェース動作
   ip addr show, ping, ifconfig
   
3. サービス層：systemd サービス動作
   systemctl status, journalctl
   
4. アプリケーション層：Flask 動作
   ps aux | grep python, curl localhost
   
5. 統合テスト：実際のデータフロー
   ESP32 送信テスト, ブラウザでダッシュボード表示
```

### 実践例

```bash
# ❌ 不効率：問題があるのに全部を修正しようとする
sudo systemctl restart hostapd dnsmasq temperature-server

# ✅ 効率的：どこに問題があるか特定してから修正
1. systemctl status hostapd         # AP が起動しているか
2. ip addr show wlan1                # IP 設定は正しいか
3. sudo hostapd_cli status           # AP が正常に動作しているか
4. sudo journalctl -u hostapd        # エラーログは何か
5. それから修正
```

---

## 🔴 教訓 3: バックグラウンドタスクの危険性

### 問題：Health Check による不意の再起動

```
【21:16:47 に発生した連鎖反応】

時刻 21:16:47
├─ health_check() 実行
├─ get_network_info() で iw コマンド実行
│  └─ ❌ 失敗：subprocess.run(['iw', ...])
│     理由：systemd サービスの PATH に /usr/sbin が含まれていない
├─ Exception 発生
├─ "AP is not running" と判定（誤った判定！）
├─ logger.warning("AP is not running, attempting to restart...")
│
├─ restart_ap() 実行
│  ├─ sudo systemctl stop hostapd
│  ├─ sudo systemctl stop dnsmasq
│  ├─ sudo systemctl start hostapd
│  └─ sudo systemctl start dnsmasq
│
└─ 結果：AP が再起動 → ESP32 の接続が切れる
   ESP32 エラー: -11 (connection refused)
```

**重要な教訓：**

> 「ヘルスチェックは患者の状態を診断するためのものなのに、
> 診断方法が失敗するせいで、患者が本当に具合悪くなる」

### 解決方法

#### オプション A：エラーハンドリング強化

```python
# services/background_tasks.py (修正前)
def health_check():
    try:
        health = wifi_manager.health_check()  # ここで例外発生
        if health.get('overall') != 'healthy':
            logger.warning(f"WiFi health: {health.get('overall')}")
    except Exception as e:
        logger.error(f"Health check error: {e}")  # ← 例外処理なし
        time.sleep(60)
```

#### オプション B：health check を無効化（このプロジェクト）

```python
# services/background_tasks.py (修正後)
def start(self):
    self.start_memory_monitor()
    # self.start_wifi_health_check()  ← コメントアウト
    self.start_log_cleanup()
```

**どちらを選ぶべきか：**
- 開発段階：health check を無効化
- 本番環境：エラーハンドリングを強化した health check を使用

---

## 🛠️ 教訓 4: systemd サービスの PATH 制限

### 問題：subprocess.run(['iw']) が見つからない

```
【通常のシェルの場合】
$ iw --version                       # ✓ 成功
python3 -c "
  import subprocess
  subprocess.run(['iw', '--version'])  # ✓ 成功
"

【systemd サービスで実行された場合】
$ sudo systemctl start temperature-server
python3 -c "
  import subprocess
  subprocess.run(['iw', '--version'])  # ❌ 失敗！
"
```

### 原因

systemd で起動されたサービスの環境：

```bash
# 通常のシェル PATH
$ echo $PATH
/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

# systemd サービスの PATH（制限されている）
# DefaultPath=/usr/local/bin:/usr/bin
# /usr/sbin が含まれていない！
```

### 解決方法

**フルパスを指定する：**

```python
# ❌ 間違い
subprocess.run(['iw', interface, 'link'])

# ✅ 正解
subprocess.run(['/usr/sbin/iw', interface, 'link'])

# さらに安全：which で確認
import shutil
iw_path = shutil.which('iw')  # → '/usr/sbin/iw'
subprocess.run([iw_path, interface, 'link'])
```

### 応用：他のコマンド

```python
# systemd サービスから外部コマンドを呼び出す場合は常にフルパス

subprocess.run(['/bin/bash', '-c', 'echo hello'])       # ✓
subprocess.run(['/usr/bin/python3', 'script.py'])       # ✓
subprocess.run(['/usr/bin/curl', 'http://example.com']) # ✓
subprocess.run(['bash', '-c', 'echo hello'])            # ✗ 危険
```

---

## 📊 教訓 5: ログを信じるな、検証しろ

### 問題：ログは嘘をつく（ことがある）

```
【レポートに記載されていた情報】
"WiFi health check: 正常に動作"
"AP 自動再起動: 実装済み"
"データベース接続: タイムアウト修正済み"

【実際のテスト結果】
curl localhost:5000 → ✓ 成功
curl 192.168.4.1:5000 → ❌ 失敗
→ 「完全に矛盾している」

【根本原因】
ログには「実施したこと」が書いてあるが、
「実施が本当に成功したか」は書いていない
```

### 正しいアプローチ

```
【信じるべきもの】
1. 実際に手で実行した test コマンドの結果
2. 自分で確認した systemctl status
3. 自分で見た journalctl ログ
4. 自分で実行した curl のレスポンス

【信じてはいけないもの】
1. 他の AI が「修正しました」と言ったレポート
2. 古いログ（時間が経っているとコード変更の影響で古い）
3. テスト環境での成功報告（本番環境で同じか不明）
4. 「問題は解決した」という一方的な報告
```

### 実践例

```bash
# ❌ 報告書を信じて終了
"温度データ送信問題：解決済み" → 記者会見で発表

# ✅ 自分で現在も検証
$ date
2025-12-24 06:07:06
$ sudo journalctl -u temperature-server -n 5
...06:07:06... "POST /api/temperature HTTP/1.1" 201
→ 「本当に今この瞬間もデータが来ている」を確認
```

---

## 🔍 教訓 6: 対照実験の設計

### 重要な検証パターン

```
【localhost vs ネットワーク経由】

test 1: curl http://127.0.0.1:5000/api/status
        → 成功ならば Flask 自体は正常

test 2: curl http://192.168.11.57:5000/api/status
        → 成功ならば wlan0 ネットワークは正常

test 3: curl http://192.168.4.1:5000/api/status
        → 成功ならば wlan1 ネットワーク + Flask は正常

test 4: ESP32 が実際に POST
        → ブラウザで 192.168.4.1:5000/api/sensors でデータ表示
        → すべてが連携している
```

**この4つのテストを段階的に実施することで、**
**どの層に問題があるかを正確に特定できます。**

---

## 🏗️ 教訓 7: システムの責任の分離

### 誤った設計

```
【すべてが health check に依存】

temperature-server サービス
  └─ background_tasks.py
      └─ health_check() が API error で例外発生
          └─ 例外をキャッチしない
              └─ systemctl restart してしまう
                  └─ 全体が不安定に
```

### 改善された設計

```
【各部分が独立して動作】

temperature-server (Flask)
  ├─ API リクエスト処理 (独立)
  ├─ データベース操作 (独立)
  └─ ユーザーインターフェース (独立)

background_tasks.py (デーモン)
  ├─ memory_monitor (CPU に直接影響なし)
  ├─ wifi_health_check (失敗しても Flask は動作)
  └─ log_cleanup (データベース操作と独立)
```

---

## 🎓 教訓 8: エラーメッセージの読み方

### 悪い例

```
エラー: [Errno 2] No such file or directory: 'iw'

→ 初心者は「iw という名前のファイルが見つからない」と理解
→ 実は「iw というコマンドが PATH に見つからない」
→ 修正方法：'/usr/sbin/iw' とフルパス指定
```

### Python 例外のパターン

```
【Errno 2: No such file or directory】
→ subprocess.run(['command']) で command が見つからない
→ 解決：which command でフルパスを調べて指定

【socket.timeout】
→ ネットワークタイムアウト
→ 解決：timeout パラメータを増やす、または接続確認

【sqlite3.OperationalError: database is locked】
→ データベースが別プロセスでロックされている
→ 解決：timeout パラメータを設定

【ConnectionRefusedError】
→ 接続先サーバーが起動していない or ポート間違い
→ 解決：サーバーが起動しているか、ポートが正しいか確認
```

---

## 📈 教訓 9: 本番環境 vs 開発環境

### 差異の例

| 項目 | 開発環境 | 本番環境 |
|------|--------|--------|
| PATH | `/usr/local/bin:/usr/bin:...` | `/usr/local/bin:/usr/bin` |
| ユーザー | `user` | `systemd` サービス用ユーザー |
| 起動方法 | `python3 run.py` | `systemctl start service` |
| ログ出力 | コンソール | `journalctl` |
| エラー処理 | 対話的にデバッグ | ログに記録のみ|

### 開発時のベストプラクティス

```bash
# 開発時は本番環境をシミュレート
sudo -u systemd-timesync bash  # systemd 的なユーザーで実行
export PATH=/usr/local/bin:/usr/bin:/usr/sbin:/sbin
python3 run.py

# または systemd サービスで実行テスト
sudo systemctl restart temperature-server
sudo journalctl -u temperature-server -f
```

---

## ✅ 教訓 10: チェックリスト駆動開発

### 重要度 100%：検証チェックリスト

新しい機能を追加したら、以下を必ず検証：

```
□ コード自体が Python 的に正しいか
  python3 -m py_compile file.py

□ ローカルホストで動作するか
  curl http://127.0.0.1:5000/api/endpoint

□ ネットワーク経由で動作するか
  curl http://192.168.4.1:5000/api/endpoint

□ systemd サービスで起動するか
  sudo systemctl restart temperature-server
  sudo systemctl status temperature-server

□ ログにエラーはないか
  sudo journalctl -u temperature-server -n 50

□ 外部コマンドはフルパスか（systemd 実行時）
  grep -r "subprocess.run\(\['" --include="*.py"

□ 複数デバイスで動作するか
  複数の ESP32 で同時テスト

□ 長時間安定動作するか
  1時間以上の連続運用テスト
```

---

## 🎯 最終的な学び

### なぜ最初は 6 時間かかったのか

1. ❌ 「ドライバが原因に違いない」と固定観念
2. ❌ 各部分を個別に検証せず全体で対応
3. ❌ ログを信じて実際に検証しない
4. ❌ systemd の PATH 制限を知らない
5. ❌ health check の危険性を過小評価

### なぜこのセッションは 6 分で解決したのか

1. ✅ 段階的に localhost → ネットワーク → ESP32 と検証
2. ✅ 実際に curl コマンドで動作確認
3. ✅ ログだけでなく実測値で判定
4. ✅ systemd サービスとシェル環境の差を意識
5. ✅ ビジネスロジック（health check）の危険性を認識

---

## 📝 今後のプロジェクト開発時の指針

```python
# ✅ 推奨：段階的実装・段階的テスト
class DualWiFiSystem:
    
    def setup(self):
        # Step 1: ドライバインストール → テスト
        self.install_driver()
        self.test_driver()
        
        # Step 2: wlan1 設定 → テスト
        self.configure_wlan1()
        self.test_wlan1_up()
        
        # Step 3: hostapd 設定 → テスト
        self.configure_hostapd()
        self.test_ap_broadcast()
        
        # Step 4: dnsmasq 設定 → テスト
        self.configure_dnsmasq()
        self.test_dhcp()
        
        # Step 5: iptables 設定 → テスト
        self.configure_iptables()
        self.test_routing()
        
        # Step 6: Flask 設定 → テスト
        self.configure_flask()
        self.test_localhost()
        self.test_network()
        
        # Step 7: 統合テスト
        self.test_esp32_integration()
```

---

**このドキュメントが、将来のプロジェクト開発者にとって、**
**6時間の試行錯誤を6分に短縮できる指針になれば幸いです。**

---

**最後に更新**: 2025年12月24日
