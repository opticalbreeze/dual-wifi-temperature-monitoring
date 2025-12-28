# 温度データ収集システム - 現状報告・検証依頼

## プロジェクト情報

### ローカル環境
- **ワークスペース**: `F:\環境データ収集システム\raspberry_pi`
- **温度サーバーディレクトリ**: `temperature_server/`

### リモートサーバー
- **ホスト**: `raspberry@192.168.1.93`
- **ディレクトリ**: `/home/raspberry/temperature_monitoring/temperature_server/`

## 現在の問題

**主な問題**: ESP32からのPOSTが受信されなくなった。サーバーが起動していない状態。

## 実施済みの作業

### 1. コード監査と修正（完了）
- ✅ `app/flask_app.py` を削除（重複解消）
- ✅ `api.py` の `insert_reading()` 返り値誤用を修正
- ✅ `app/__init__.py` の冗長なログミドルウェアを修正
- ✅ テストファイル `test_api_validation.py` を削除（存在しないモジュール参照）
- ✅ `api.py` の `data` が `None` の場合のエラーハンドリングを追加

### 2. ファイル転送（完了）
- ✅ 修正した `app/routes/api.py` をリモートサーバーに転送済み
- ✅ 修正した `app/__init__.py` をリモートサーバーに転送済み

### 3. 修正内容の詳細

#### `api.py` の修正
- **問題**: `data` が `None` の場合（JSONデコード失敗時）に `data.get()` を呼ぶと `AttributeError` が発生
- **修正**: `data` が `None` かどうかを先にチェックし、早期リターンするように変更

```python
# 修正前（問題あり）
data = request.get_json(force=True, silent=True)
sensor_id = data.get('device_id') or data.get('sensor_id')  # dataがNoneの場合エラー

# 修正後
data = request.get_json(force=True, silent=True)
if not data:
    return jsonify({"status": "error", "message": "Invalid JSON format"}), 400
sensor_id = data.get('device_id') or data.get('sensor_id')  # 安全
```

## 現在の状況

### サーバーの状態
- ❌ **サーバーが起動していない**
- ❌ ポート5000が既に使用中（別プロセスが占有している可能性）
- ✅ 修正したコードはリモートサーバーに転送済み

### 確認済みの事実
- 修正した `api.py` はリモートサーバーに転送済み（6065バイト）
- サーバープロセスが見つからない（`ps aux | grep 'python.*run.py'` で確認）
- ポート5000が使用中（`Address already in use` エラー）

## 必要な対応（優先順位順）

### 🔴 最優先: サーバーの起動

**問題**: サーバーが起動していない。ポート5000が使用中。

**解決手順**:

1. **ポート5000を使用しているプロセスを特定・停止**
   ```bash
   # 方法1: lsofを使用（推奨）
   ssh raspberry@192.168.1.93 "lsof -ti:5000 | xargs kill -9"
   
   # 方法2: fuserを使用
   ssh raspberry@192.168.1.93 "fuser -k 5000/tcp"
   
   # 方法3: netstatでプロセスを特定してからkill
   ssh raspberry@192.168.1.93 "netstat -tlnp | grep 5000"
   # 出力されたPIDを確認してから
   ssh raspberry@192.168.1.93 "kill -9 <PID>"
   ```

2. **サーバーを起動**
   ```bash
   ssh raspberry@192.168.1.93 "cd ~/temperature_monitoring/temperature_server && source venv/bin/activate && nohup python run.py > server.log 2>&1 &"
   ```

3. **起動確認**
   ```bash
   # プロセス確認
   ssh raspberry@192.168.1.93 "ps aux | grep 'python.*run.py' | grep -v grep"
   
   # ログ確認
   ssh raspberry@192.168.1.93 "tail -20 ~/temperature_monitoring/temperature_server/server.log"
   
   # ポート確認
   ssh raspberry@192.168.1.93 "netstat -tlnp | grep 5000"
   ```

### ⚠️ 次: ESP32からのPOST受信確認

サーバーが起動したら、以下でESP32からのPOST受信を確認：

```bash
# リアルタイムでログを監視
ssh raspberry@192.168.1.93 "tail -f ~/temperature_monitoring/temperature_server/logs/app.routes.api.log"

# または最新30行を確認
ssh raspberry@192.168.1.93 "tail -30 ~/temperature_monitoring/temperature_server/logs/app.routes.api.log"
```

**期待されるログ出力**（修正後のコードが読み込まれている場合）：
```
[POST /api/temperature] リクエスト受信
IP: 192.168.4.xxx
リクエストヘッダー: {...}
Content-Type: application/json
Content-Length: xxx
生リクエストボディ: {...}
JSONデコード結果: {...}
バリデーション - sensor_id: ..., temperature: ...
DB挿入開始 - sensor_id: ..., temp: ..., name: ..., humidity: ...
✅ データ保存成功 - Device: ..., Name: ..., Location: ..., Temp: ...°C
============================================================
```

## トラブルシューティング

### ポート5000が解放されない場合

1. **systemdサービスが起動している可能性**
   ```bash
   ssh raspberry@192.168.1.93 "systemctl status temperature-server"
   ssh raspberry@192.168.1.93 "sudo systemctl stop temperature-server"
   ```

2. **別のFlaskアプリケーションが起動している可能性**
   ```bash
   ssh raspberry@192.168.1.93 "ps aux | grep python | grep -E 'flask|run.py|app'"
   ```

3. **強制的にポートを解放**
   ```bash
   ssh raspberry@192.168.1.93 "sudo fuser -k 5000/tcp"
   ```

### サーバーが起動しない場合

1. **エラーログを確認**
   ```bash
   ssh raspberry@192.168.1.93 "cat ~/temperature_monitoring/temperature_server/server.log"
   ```

2. **venvが正しく有効化されているか確認**
   ```bash
   ssh raspberry@192.168.1.93 "cd ~/temperature_monitoring/temperature_server && source venv/bin/activate && which python && python --version"
   ```

3. **依存関係を確認**
   ```bash
   ssh raspberry@192.168.1.93 "cd ~/temperature_monitoring/temperature_server && source venv/bin/activate && pip list | grep -E 'flask|flask-cors'"
   ```

## 重要なファイルパス

### ローカル
- APIルート: `F:\環境データ収集システム\raspberry_pi\temperature_server\app\routes\api.py`
- アプリ初期化: `F:\環境データ収集システム\raspberry_pi\temperature_server\app\__init__.py`
- 設定ファイル: `F:\環境データ収集システム\raspberry_pi\temperature_server\config.py`

### リモートサーバー
- プロジェクトルート: `/home/raspberry/temperature_monitoring/temperature_server/`
- APIログ: `/home/raspberry/temperature_monitoring/temperature_server/logs/app.routes.api.log`
- サーバーログ: `/home/raspberry/temperature_monitoring/temperature_server/server.log`
- データベース: `/home/raspberry/temperature_monitoring/temperature_server/data/temperature.db`

## 修正済みコードの確認

### `api.py` の修正箇所
- 行32-42: `data` が `None` の場合のチェックを追加
- 行57: `insert_reading()` の返り値を受け取らないように修正（`result` 変数を削除）

### `app/__init__.py` の修正箇所
- 行11: 未使用の `datetime` インポートを削除
- 行27-35: 冗長な条件分岐を削除、シンプルなログ出力に統一

## 次のステップ

1. **ポート5000を解放**（上記の手順を実行）
2. **サーバーを起動**（上記の手順を実行）
3. **起動を確認**（プロセスとログを確認）
4. **ESP32からのPOST受信を確認**（ログを監視）
5. **データベースへの保存を確認**（必要に応じて）

## 技術スタック

- **サーバー**: Flask (Python)
- **データベース**: SQLite
- **ロギング**: Python logging（ファイル出力）
- **実行環境**: Raspberry Pi OS (Linux)
- **Python環境**: venv (`~/temperature_monitoring/temperature_server/venv/`)

## 注意事項

- リモートサーバーに接続する際はパスワード認証が必要
- venvを有効化してからサーバーを起動する必要がある（`source venv/bin/activate`）
- ポート5000が既に使用中の場合は、既存プロセスを停止する必要がある
- ログファイルは `logs/` ディレクトリに保存される（`app.routes.api.log` がAPIのログ）
- 修正したコードは既にリモートサーバーに転送済み（2025年12月28日時点）

## 過去の問題と解決

### 問題1: `data` が `None` の場合のエラー
- **症状**: `AttributeError: 'NoneType' object has no attribute 'get'`
- **原因**: JSONデコード失敗時に `data` が `None` になり、`data.get()` を呼んでいた
- **解決**: `data` が `None` かどうかを先にチェックするように修正

### 問題2: サーバーが起動しない
- **症状**: `Address already in use` エラー
- **原因**: ポート5000が既に使用中
- **解決**: 既存プロセスを停止してから再起動（上記手順参照）
