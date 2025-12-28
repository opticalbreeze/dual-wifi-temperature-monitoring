# ドキュメント・スクリプト整理サマリー

整理日: 2025-12-27

## ✅ 実施内容

### 1. ドキュメント整理

#### 削除したドキュメント（12個）

- `CODE_AUDIT_REPORT.md` - 一時的な分析レポート
- `CLEANUP_SUMMARY.md` - 一時的な分析レポート
- `HARDCODING_FIX_SUMMARY.md` - 一時的な分析レポート
- `UNUSED_FUNCTION_ANALYSIS.md` - 一時的な分析レポート
- `UNIFIED_SETUP.md` - 重複ドキュメント
- `temperature_server/docs/LESSONS_LEARNED.md` - 開発過程の記録
- `temperature_server/docs/README.md` - メインREADMEに統合
- `temperature_server/docs/GITHUB_PUSH_GUIDE.md` - 一般的なGit操作
- `free_wifi/README_old.md` - 古いREADME
- `free_wifi/CHANGES.md` - Git履歴で管理
- `free_wifi/GITHUB_PUSH_GUIDE.md` - 一般的なGit操作
- `free_wifi/MAIN_CODE_GUIDE.md` - コードにコメントがあるため不要
- `free_wifi/SETUP_RASPBERRYPI.md` - SETUP.mdに統合
- `free_wifi/BEGINNER_GUIDE.md` - SETUP.mdに統合

#### 統合・移動したドキュメント

- `README_UNIFIED.md` → `README.md`（メインREADME）
- `NEW_PROJECT_SETUP.md` → `docs/SETUP.md`
- `temperature_server/docs/WIFI_SETUP.md` → `docs/DUAL_WIFI_SETUP.md`
- `MIGRATION_GUIDE.md` → `docs/MIGRATION.md`
- `CREATE_NEW_REPO.md` → `docs/CREATE_REPO.md`
- `temperature_server/docs/ARCHITECTURE.md` → `docs/ARCHITECTURE.md`
- `temperature_server/docs/TROUBLESHOOTING.md` → `docs/TROUBLESHOOTING.md`
- `temperature_server/docs/ESP32_CODE.md` → `docs/ESP32_SETUP.md`
- `free_wifi/RASPBERRYPI_REQUIREMENTS.md` → `docs/REQUIREMENTS.md`（統合・更新）

#### 最終的なdocs/構成

```
docs/
├── SETUP.md                 # 新規セットアップガイド
├── DUAL_WIFI_SETUP.md       # デュアルWiFi設定（詳細）
├── TROUBLESHOOTING.md       # トラブルシューティング
├── ESP32_SETUP.md           # ESP32コード・設定ガイド
├── ENVIRONMENT_VARIABLES.md # 環境変数設定ガイド
├── ARCHITECTURE.md          # アーキテクチャ詳細
├── REQUIREMENTS.md          # システム要件
├── MIGRATION.md             # 移行ガイド
└── CREATE_REPO.md           # 新規リポジトリ作成ガイド
```

### 2. スクリプト整理

#### 削除したスクリプト（10個）

- `setup.sh` - 古いセットアップ（server.py参照）
- `setup_ap.sh` - setup_dual_wifi.shと重複
- `setup_ap_auto.sh` - wlan1-setup.serviceと重複
- `install_wifi_ap_auto.sh` - install_wlan1_setup.shと重複
- `fix_ap.sh` - setup_dual_wifi.shで代替可能
- `deploy.sh` - 開発用、新しいプロジェクトでは不要
- `setup-wifi-ap.service` - wlan1-setup.serviceに置き換え
- `temperature_server/setup_phase1.sh` - setup_unified_venv.shで代替
- `free_wifi/ファイル/tester/guest2-rep.sh` - テストスクリプト
- `free_wifi/ファイル/tester/update-webdriver.sh` - 重複

#### 移動したスクリプト

- `diagnose.sh` → `scripts/diagnose.sh`（更新）
- `fix_services.sh` → `scripts/fix_services.sh`（更新）
- `temperature_server/restart_services.sh` → `scripts/restart_services.sh`（更新）

#### 最終的なスクリプト構成

```
ルート/
├── setup_unified_venv.sh       # ✅ 統合環境セットアップ
├── setup_dual_wifi.sh          # ✅ デュアルWiFi設定
├── start_temperature_server.sh # ✅ 温度サーバー起動
├── start_free_wifi.sh          # ✅ FREE_Wifi起動
├── setup_wlan1.sh              # ✅ wlan1設定
├── install_wlan1_setup.sh      # ✅ wlan1自動設定インストール
└── scripts/                    # 新規作成
    ├── diagnose.sh             # ✅ システム診断
    ├── fix_services.sh         # ✅ サービス修復
    └── restart_services.sh     # ✅ サービス再起動

temperature_server/
└── systemd/
    └── install_service.sh      # ✅ systemdサービスインストール

free_wifi/
├── start.sh                    # ✅ 起動スクリプト
├── install.sh                  # ✅ インストールスクリプト
├── install_autostart.sh        # ✅ 自動起動インストール
├── uninstall_autostart.sh      # ✅ 自動起動解除
└── update_webdriver.sh         # ✅ WebDriver更新
```

## 📊 統計

- **削除したドキュメント**: 14個
- **削除したスクリプト**: 10個
- **統合・移動したドキュメント**: 9個
- **移動したスクリプト**: 3個
- **作成したディレクトリ**: 2個（`docs/`, `scripts/`）

## ✅ 完了

すべての整理作業が完了しました。プロジェクト構造がより明確になり、メンテナンスしやすくなりました。

