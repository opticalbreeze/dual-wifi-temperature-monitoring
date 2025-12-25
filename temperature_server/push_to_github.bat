@echo off
REM Git Push Script for dual-wifi-temperature-monitoring
REM このスクリプトを実行するには、ダブルクリックしてください

setlocal enabledelayedexpansion

echo ========================================
echo デュアル WiFi 温度監視システム
echo GitHub Push スクリプト
echo ========================================
echo.

cd /d I:\ESP32DS18\raspberry_pi\temperature_server

if errorlevel 1 (
    echo エラー: ディレクトリに移動できません
    echo I:\ESP32DS18\raspberry_pi\temperature_server
    pause
    exit /b 1
)

echo 現在のディレクトリ: %cd%
echo.

REM Git が見つかるか確認
where git >nul 2>&1
if errorlevel 1 (
    echo エラー: Git がインストールされていません
    echo https://git-scm.com/download/win からインストールしてください
    pause
    exit /b 1
)

echo ✓ Git がインストールされています
echo.

REM Git 初期化
if not exist .git (
    echo Git リポジトリを初期化しています...
    git init
    git config user.name "Temperature Server Developer"
    git config user.email "opticalbreeze@github.com"
) else (
    echo ✓ Git リポジトリは既に初期化されています
)

echo.
echo ========== 現在のステータス ==========
git status
echo.

echo ========== ファイルをステージングします ==========
git add -A
echo ✓ 完了

echo.
echo ========== コミットを作成します ==========
git commit -m "Initial commit: Complete dual WiFi temperature monitoring system with comprehensive documentation

- 7 comprehensive markdown documents
- Complete Raspberry Pi dual WiFi setup guide
- RTL8821AU driver installation instructions
- Flask REST API server implementation
- SQLite database with persistent storage
- Real-time web dashboard
- ESP32 microcontroller implementation guide
- 10 lessons learned from 6+ hour development crisis
- Detailed troubleshooting guide"

if errorlevel 1 (
    echo すでにコミットされている可能性があります
)

echo.
echo ========== リモートを設定します ==========
git remote remove origin 2>nul || true
git remote add origin https://github.com/opticalbreeze/dual-wifi-temperature-monitoring.git
echo ✓ リモート設定完了

echo.
echo ========== メインブランチを確認します ==========
git branch -M main

echo.
echo ========== GitHub にプッシュします ==========
echo このステップで認証が求められる場合があります。GitHub の認証情報を入力してください。
echo.

git push -u origin main

if errorlevel 1 (
    echo.
    echo ✗ プッシュに失敗しました
    echo 以下を確認してください：
    echo   1. GitHub の認証情報が正しいか
    echo   2. リポジトリ URL が正しいか: https://github.com/opticalbreeze/dual-wifi-temperature-monitoring
    echo   3. ネットワーク接続があるか
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✓ プッシュ完了！
echo ========================================
echo.
echo リポジトリ URL:
echo https://github.com/opticalbreeze/dual-wifi-temperature-monitoring
echo.
pause
