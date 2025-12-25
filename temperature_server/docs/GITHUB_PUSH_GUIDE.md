# GitHub へのプッシュ手順

このドキュメントでは、プロジェクトを GitHub にプッシュする方法を説明します。

---

## 🚀 自動プッシュスクリプト

### Windows ユーザー

1. ファイルエクスプローラーで以下を開きます：
   ```
   i:\ESP32DS18\raspberry_pi\temperature_server\
   ```

2. `push_to_github.bat` をダブルクリック

3. Git 認証画面が表示されたら、GitHub の認証情報を入力

4. 完了！ 🎉

### macOS / Linux ユーザー

```bash
cd /path/to/dual-wifi-temperature-monitoring
bash push_to_github.sh
```

---

## 📋 手動プッシュ手順

スクリプトが動作しない場合は、以下を手動で実行してください：

### ステップ 1：ディレクトリに移動

```bash
cd i:\ESP32DS18\raspberry_pi\temperature_server
```

### ステップ 2：Git を初期化（初回のみ）

```bash
git init
git config user.name "Your Name"
git config user.email "your-email@github.com"
```

### ステップ 3：リモートを追加

```bash
git remote add origin https://github.com/opticalbreeze/dual-wifi-temperature-monitoring.git
```

### ステップ 4：ファイルをステージング

```bash
git add -A
```

### ステップ 5：コミットを作成

```bash
git commit -m "Initial commit: Complete dual WiFi temperature monitoring system with comprehensive documentation"
```

### ステップ 6：ブランチを確認

```bash
git branch -M main
```

### ステップ 7：GitHub にプッシュ

```bash
git push -u origin main
```

---

## 🔑 GitHub 認証

### Personal Access Token の使用（推奨）

Windows の認証情報マネージャーを使用している場合：

1. GitHub の設定 → Developer settings → Personal access tokens
2. 新しいトークンを作成（`repo` スコープを選択）
3. トークンをコピー
4. Git プッシュ時にパスワード欄にトークンを貼り付け

### SSH キーの使用（高度な方法）

```bash
# SSH キーを生成（初回のみ）
ssh-keygen -t ed25519 -C "your-email@github.com"

# GitHub に公開鍵を追加
# https://github.com/settings/keys

# リモート URL を SSH に変更
git remote set-url origin git@github.com:opticalbreeze/dual-wifi-temperature-monitoring.git

# プッシュ
git push -u origin main
```

---

## ✅ プッシュ確認

プッシュが完了したら、GitHub で確認できます：

```
https://github.com/opticalbreeze/dual-wifi-temperature-monitoring
```

以下の項目がリポジトリに含まれているか確認してください：

- ✓ MAIN_README.md（メインドキュメント）
- ✓ docs/README.md
- ✓ docs/ARCHITECTURE.md
- ✓ docs/WIFI_SETUP.md
- ✓ docs/SETUP_GUIDE.md
- ✓ docs/LESSONS_LEARNED.md
- ✓ docs/TROUBLESHOOTING.md
- ✓ docs/ESP32_CODE.md
- ✓ app/（アプリケーションコード）
- ✓ services/（サービスコード）
- ✓ database/（データベースコード）
- ✓ templates/（Web UI）
- ✓ .gitignore
- ✓ config.py
- ✓ requirements.txt
- ✓ server.py

---

## 🆘 トラブルシューティング

### エラー：Authentication failed

```
error: failed to push some refs to 'https://github.com/opticalbreeze/dual-wifi-temperature-monitoring.git'
```

**解決方法：**
1. GitHub パスワードまたはトークンが正しいか確認
2. リポジトリにプッシュ権限があるか確認
3. Windows 認証情報マネージャーをリセット：
   ```bash
   git credential reject https://github.com
   # 次回のプッシュで再度認証
   ```

### エラー：The remote repository does not exist

```
fatal: repository 'https://github.com/opticalbreeze/dual-wifi-temperature-monitoring.git' not found
```

**解決方法：**
1. GitHub でリポジトリが作成されているか確認
2. リポジトリ URL が正しいか確認
3. リモート URL を確認：
   ```bash
   git remote -v
   ```

### エラー：Permission denied (publickey)

```
Permission denied (publickey).
fatal: Could not read from remote repository.
```

**解決方法：**
SSH キーが正しく設定されているか確認：
```bash
ssh -T git@github.com
```

---

## 📊 プッシュ後の確認

リポジトリが正常にプッシュされたか確認するには：

```bash
# ローカルで確認
git log --oneline -5

# GitHub で確認
https://github.com/opticalbreeze/dual-wifi-temperature-monitoring/commits/main
```

---

## 🔄 継続的な更新

今後、ドキュメントやコードに更新がある場合：

```bash
# 変更を確認
git status

# ファイルをステージング
git add -A

# コミットを作成
git commit -m "Update documentation or code changes"

# プッシュ
git push origin main
```

---

**最後に更新**: 2025年12月24日
