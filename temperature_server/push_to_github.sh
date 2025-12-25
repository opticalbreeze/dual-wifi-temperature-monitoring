#!/bin/bash
# Git Push Script for dual-wifi-temperature-monitoring

echo "=== デュアル WiFi 温度監視システム - GitHub Push スクリプト ==="
echo ""

# ディレクトリに移動
cd /i/ESP32DS18/raspberry_pi/temperature_server || cd i:\\ESP32DS18\\raspberry_pi\\temperature_server

echo "現在のディレクトリ: $(pwd)"
echo ""

# Git 初期化（既に初期化されていない場合）
if [ ! -d .git ]; then
    echo "Git リポジトリを初期化します..."
    git init
    git config user.name "Temperature Server Developer"
    git config user.email "opticalbreeze@github.com"
else
    echo "✓ Git リポジトリは既に初期化されています"
fi

echo ""
echo "=== 変更内容の確認 ==="
git status

echo ""
echo "=== ファイルをステージングします... ==="
git add -A

echo ""
echo "=== コミットを作成します... ==="
git commit -m "Initial commit: Complete dual WiFi temperature monitoring system with comprehensive documentation

- 7つの詳細なドキュメント（README, ARCHITECTURE, WIFI_SETUP, SETUP_GUIDE, LESSONS_LEARNED, TROUBLESHOOTING, ESP32_CODE）
- Raspberry Pi のデュアル WiFi セットアップ完全ガイド
- RTL8821AU ドライバのインストール手順
- Flask REST API サーバー実装
- SQLite データベース
- リアルタイム Web ダッシュボード
- ESP32 マイコン実装ガイド
- 6時間の開発過程で学んだ10の教訓
- 詳細なトラブルシューティングガイド"

echo ""
echo "=== リモートリポジトリを追加します... ==="
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/opticalbreeze/dual-wifi-temperature-monitoring.git

echo ""
echo "=== ブランチを確認... ==="
git branch -M main

echo ""
echo "=== GitHub にプッシュします... ==="
git push -u origin main -v

echo ""
echo "✓ プッシュ完了！"
echo "リポジトリ: https://github.com/opticalbreeze/dual-wifi-temperature-monitoring"
