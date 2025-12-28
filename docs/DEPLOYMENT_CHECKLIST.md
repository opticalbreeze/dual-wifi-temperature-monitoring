# 本番環境デプロイ前チェックリスト

**作成日:** 2025年12月27日  
**対象:** 本番環境へのデプロイ  
**目的:** 本番化前の完全チェック

---

## デプロイフェーズ別チェック

### 📋 Phase 1: セキュリティチェック（必須）

#### 🔐 認証情報

- [ ] **SECRET_KEY が変更されている**
  ```bash
  grep "^SECRET_KEY=" .env | grep -v "dev-secret-key"
  ```
  
  ✅ 実行結果例：
  ```bash
  SECRET_KEY=abc123def456...  # ✓ ランダムな値
  ```

- [ ] **AP_PASSWORD が安全に設定されている**
  ```bash
  grep "^AP_PASSWORD=" .env | wc -c  # 8文字以上か確認
  ```
  
  ✅ 実行結果例：
  ```bash
  # 12文字以上であること
  AP_PASSWORD=secure_password_123!
  ```

- [ ] **TAILSCALE_AUTH_KEY が正しい形式**（Tailscale使用時）
  ```bash
  grep "^TAILSCALE_AUTH_KEY=" .env | grep -E "tskey-[a-zA-Z0-9]+"
  ```

#### 🔒 Flask セキュリティ

- [ ] **FLASK_DEBUG が False に設定**
  ```bash
  grep "^FLASK_DEBUG=False" .env
  ```

- [ ] **FLASK_ENV が production に設定**
  ```bash
  grep "^FLASK_ENV=production" .env
  ```

#### 🛡️ CORS 設定

- [ ] **ALLOWED_ORIGINS がホワイトリスト方式**
  ```bash
  grep "^ALLOWED_ORIGINS=" .env | grep -v "*"
  ```
  
  ⚠️ ワイルドカード（`*`）が含まれていないこと

- [ ] **許可するオリジンが限定されている**
  ```bash
  # 本番環境では 1-2 個のオリジンのみ推奨
  ALLOWED_ORIGINS=http://192.168.4.1:5000
  ```

#### 🔐 ログレベル

- [ ] **LOG_LEVEL が WARNING 以上に設定**
  ```bash
  grep "^LOG_LEVEL=" .env | grep -E "(WARNING|ERROR|CRITICAL)"
  ```

#### 📂 ファイル管理

- [ ] **.gitignore に .env が含まれている**
  ```bash
  grep "^\.env$" .gitignore
  ```

- [ ] **.env がリポジトリに含まれていない**
  ```bash
  git status | grep ".env"  # 何も表示されなければ OK
  ```

- [ ] **git log に機密情報がない**
  ```bash
  git log --all --full-history | grep -E "SECRET_KEY|PASSWORD" | wc -l
  # 0 であること
  ```

---

### 🗂️ Phase 2: コードチェック

#### 📝 ハードコード チェック

- [ ] **config.py にハードコード認証情報がない**
  ```bash
  grep -r "PASSWORD\|SECRET\|AUTH" \
    temperature_server/config.py \
    free_wifi/config.py | grep -v "os.getenv"
  # 何も表示されなければ OK
  ```

- [ ] **API キーが環境変数から読み込まれている**
  ```bash
  grep -r "TAILSCALE_AUTH_KEY" temperature_server/ | grep "os.getenv"
  ```

#### 🧪 テストカバレッジ

- [ ] **ユニットテストが実装されている**
  ```bash
  find . -name "test_*.py" -o -name "*_test.py" | wc -l
  # 最低 5 個以上のテストが存在
  ```

- [ ] **テストがすべてパスしている**
  ```bash
  python -m pytest --tb=short
  # FAILED がないこと
  ```

- [ ] **カバレッジが 80% 以上**
  ```bash
  python -m pytest --cov=. --cov-report=term-missing
  # TOTAL が 80% 以上
  ```

#### 📚 コード品質

- [ ] **Lint エラーがない**
  ```bash
  python -m pylint temperature_server/ free_wifi/ --fail-under=7
  ```

- [ ] **型チェック警告が少ない**
  ```bash
  python -m mypy temperature_server/ free_wifi/ 2>&1 | grep -c "error"
  # 10 以下であること
  ```

---

### 🌐 Phase 3: インフラストラクチャチェック

#### 🔌 ネットワーク設定

- [ ] **Firewall ルールが適切に設定**
  - [ ] ポート 5000 (Flask) が許可されている
  - [ ] SSH (ポート 22) がホワイトリストに限定
  - [ ] 不要なポートが開いていない

#### 💾 ディスク・メモリ

- [ ] **ディスク空き容量が 1GB 以上**
  ```bash
  df -h | grep "/" | awk '{print $4}'
  ```

- [ ] **メモリが十分にある**
  ```bash
  free -m | grep "Mem:" | awk '{print $7}'
  # 256MB 以上推奨
  ```

#### 🔄 バックアップ

- [ ] **データベースバックアップが取得可能**
  ```bash
  sqlite3 temperature_server/data/temperature.db ".tables"
  ```

- [ ] **ログディレクトリが書き込み可能**
  ```bash
  touch temperature_server/logs/.test && rm temperature_server/logs/.test
  ```

---

### 🚀 Phase 4: デプロイテスト

#### 🧪 ローカルテスト

- [ ] **temperature_server が起動できる**
  ```bash
  cd temperature_server
  python run.py &
  sleep 5
  curl http://localhost:5000/
  kill %1
  ```
  
  期待結果: HTTP 200 OK

- [ ] **free_wifi が起動できる**
  ```bash
  cd free_wifi
  python main.py &
  sleep 5
  # 画面が表示されるか確認
  kill %1
  ```

- [ ] **API エンドポイントが応答する**
  ```bash
  curl -X POST http://localhost:5000/api/temperature \
    -H "Content-Type: application/json" \
    -d '{"sensor_id":"test_sensor","temperature":25.5}'
  ```
  
  期待結果: `{"status":"success","received":true}`

#### 🔒 セキュリティテスト

- [ ] **CORS が正しく機能している**
  ```bash
  curl -i -H "Origin: http://evil.com" \
    http://localhost:5000/api/temperature
  ```
  
  期待結果: CORS ヘッダーが **返されない**

- [ ] **SQL インジェクション対策が機能**
  ```bash
  curl -X POST http://localhost:5000/api/temperature \
    -H "Content-Type: application/json" \
    -d '{"sensor_id":"test; DROP TABLE temperatures;--","temperature":25.5}'
  ```
  
  期待結果: バリデーションエラー

- [ ] **XSS 対策が機能**
  ```bash
  curl -X POST http://localhost:5000/api/temperature \
    -H "Content-Type: application/json" \
    -d '{"sensor_id":"<script>alert(1)</script>","temperature":25.5}'
  ```
  
  期待結果: バリデーションエラー

#### 📊 ログテスト

- [ ] **ログが機密情報をマスクしている**
  ```bash
  tail temperature_server/logs/main.log | grep -E "PASSWORD|SECRET"
  # 何も表示されなければ OK
  ```

- [ ] **ログローテーションが機能している**
  ```bash
  ls -la temperature_server/logs/
  # 複数の .log.* ファイルが存在すること
  ```

---

### 🔧 Phase 5: 本番環境セットアップ

#### 📦 依存関係

- [ ] **requirements-all.txt が最新**
  ```bash
  pip freeze > /tmp/current_deps.txt
  diff /tmp/current_deps.txt requirements-all.txt
  ```

- [ ] **仮想環境が独立している**
  ```bash
  which python  # venv パスであること
  pip list | grep -E "Flask|Django" | wc -l
  ```

#### 🔄 systemd サービス

- [ ] **temperature_server.service が登録されている**
  ```bash
  sudo systemctl status temperature-server
  ```

- [ ] **guest2-repeater.service が登録されている**（free_wifi用）
  ```bash
  sudo systemctl status guest2-repeater 2>/dev/null || echo "Not required"
  ```

- [ ] **サービスが自動起動に設定されている**
  ```bash
  sudo systemctl is-enabled temperature-server
  # enabled であること
  ```

#### 📝 設定ファイル

- [ ] **hostapd.conf が正しく設定**
  ```bash
  sudo cat /etc/hostapd/hostapd.conf | grep -E "ssid|wpa_passphrase"
  ```

- [ ] **dnsmasq.conf が正しく設定**
  ```bash
  sudo cat /etc/dnsmasq.conf | grep -E "interface|dhcp-range"
  ```

#### 🔐 権限設定

- [ ] **ログディレクトリの権限が適切**
  ```bash
  ls -la temperature_server/logs/
  # 出力： drwxr-xr-x ... logs/
  ```

- [ ] **データベースファイルの権限が適切**
  ```bash
  ls -la temperature_server/data/
  # 出力： -rw-r--r-- ... temperature.db
  ```

---

### 📡 Phase 6: 本番環境検証

#### 🌍 アクセス確認

- [ ] **外部からダッシュボードにアクセス可能**
  ```bash
  curl http://192.168.4.1:5000/
  # HTTP 200 OK
  ```

- [ ] **API からデータ送受信が可能**
  ```bash
  curl http://192.168.4.1:5000/api/status
  # JSON レスポンス
  ```

#### 🔄 自動起動確認

- [ ] **システム再起動後も自動起動**
  ```bash
  sudo reboot
  # 再起動後、サービスが起動しているか確認
  sudo systemctl status temperature-server
  ```

#### 📊 ログ監視

- [ ] **エラーログが出力されていない**
  ```bash
  grep "ERROR\|CRITICAL" temperature_server/logs/main.log | wc -l
  # 0 に近い値
  ```

- [ ] **パフォーマンス統計が記録されている**
  ```bash
  tail -f temperature_server/logs/main.log
  # ログが定期的に出力されること
  ```

#### 💾 バックアップ確認

- [ ] **自動バックアップが動作している**
  ```bash
  ls -la temperature_server/data/
  # backup/ ディレクトリが存在し、ファイルがあること
  ```

#### 🔒 セキュリティ監査

- [ ] **ファイアウォール設定を確認**
  ```bash
  sudo ufw status
  # Status: active で、必要なポートのみ許可
  ```

- [ ] **SSH キー認証が有効**
  ```bash
  grep "PasswordAuthentication" /etc/ssh/sshd_config
  # no であること
  ```

- [ ] **root ログイン が無効**
  ```bash
  grep "PermitRootLogin" /etc/ssh/sshd_config
  # no であること
  ```

---

## チェックリスト実行スクリプト

**ファイル:** `check_production_ready.sh`

```bash
#!/bin/bash
# 本番環境デプロイ前の自動チェック

set -e

echo "=========================================="
echo "本番環境デプロイ前チェック"
echo "=========================================="

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

passed=0
failed=0

# チェック関数
check() {
    local name=$1
    local cmd=$2
    
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name"
        ((passed++))
    else
        echo -e "${RED}✗${NC} $name"
        ((failed++))
    fi
}

# ===== セキュリティチェック =====
echo -e "\n${YELLOW}セキュリティチェック${NC}"

check "SECRET_KEY が設定されている" \
    "grep -q '^SECRET_KEY=' .env && [ $(grep '^SECRET_KEY=' .env | cut -d= -f2 | wc -c) -gt 32 ]"

check "AP_PASSWORD が8文字以上" \
    "grep -q '^AP_PASSWORD=' .env && [ $(grep '^AP_PASSWORD=' .env | cut -d= -f2 | wc -c) -ge 9 ]"

check "FLASK_DEBUG が False" \
    "grep -q '^FLASK_DEBUG=False' .env"

check "FLASK_ENV が production" \
    "grep -q '^FLASK_ENV=production' .env"

check ".gitignore に .env が含まれている" \
    "grep -q '^\\.env$' .gitignore"

# ===== コードチェック =====
echo -e "\n${YELLOW}コードチェック${NC}"

check "テストファイルが存在" \
    "find . -name 'test_*.py' | wc -l | grep -qE '[5-9]|[0-9]{2,}'"

check "テストがすべてパスしている" \
    "python -m pytest -q 2>&1 | grep -q 'passed'"

# ===== インフラチェック =====
echo -e "\n${YELLOW}インフラストラクチャチェック${NC}"

check "ディスク空き容量が1GB以上" \
    "df -BG / | awk 'NR==2 {print \$4}' | sed 's/G//' | awk '{exit \$1 >= 1}'"

check "メモリが256MB以上" \
    "free -m | awk 'NR==2 {print \$7}' | awk '{exit \$1 >= 256}'"

check "temperature_server ディレクトリが存在" \
    "[ -d 'temperature_server' ]"

check "free_wifi ディレクトリが存在" \
    "[ -d 'free_wifi' ]"

# ===== 結果出力 =====
echo -e "\n=========================================="
echo -e "${GREEN}合格: $passed${NC}"
echo -e "${RED}失敗: $failed${NC}"
echo "=========================================="

if [ $failed -gt 0 ]; then
    echo -e "\n${RED}❌ デプロイ前にエラーを修正してください${NC}"
    exit 1
else
    echo -e "\n${GREEN}✅ 本番環境へのデプロイ準備完了${NC}"
    exit 0
fi
```

**実行:**
```bash
chmod +x check_production_ready.sh
./check_production_ready.sh
```

---

## よくある問題と解決方法

### Q: SECRET_KEY を忘れてしまった

**A:** 新しいキーを生成して設定
```bash
openssl rand -hex 32 >> .env
# 既存の SECRET_KEY をコメントアウト
```

### Q: デプロイ後、CORS エラーが出ている

**A:** ALLOWED_ORIGINS を確認・追加
```bash
# 現在の ALLOWED_ORIGINS を確認
grep "^ALLOWED_ORIGINS=" .env

# アクセス元を追加
# 例: http://example.com:5000 から来ている場合
ALLOWED_ORIGINS=http://192.168.4.1:5000,http://example.com:5000
```

### Q: ログが大きくなりすぎた

**A:** ログをクリーンアップ
```bash
# 古いログを削除
find temperature_server/logs/ -name "*.log.*" -mtime +7 -delete

# または、ログをアーカイブ
tar czf logs_backup.tar.gz temperature_server/logs/
rm temperature_server/logs/*.log.*
```

---

## デプロイ成功チェック

本番環境で以下を確認してください：

```bash
# 最終確認

echo "🔐 セキュリティ"
grep "SECRET_KEY\|AP_PASSWORD" .env | grep -v "^#"

echo "📊 サービス状態"
sudo systemctl status temperature-server
sudo systemctl status guest2-repeater 2>/dev/null || echo "Not required"

echo "📝 最新ログ"
tail -n 5 temperature_server/logs/main.log

echo "✅ デプロイ完了！"
```

---

**最終更新:** 2025年12月27日  
**バージョン:** 1.0
