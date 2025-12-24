# コード監査レポート

**対象ファイル:** `app/routes/api.py`  
**監査日:** 2025年12月24日  
**監査観点:** セキュリティ、冗長性、メンテナンス性

---

## 目次
1. [監査概要](#監査概要)
2. [セキュリティ面での問題](#セキュリティ面での問題)
3. [冗長なコード](#冗長なコード)
4. [無駄な変数・処理](#無駄な変数処理)
5. [構造とメンテナンス性](#構造とメンテナンス性)
6. [改善版コード](#改善版コード)
7. [実装推奨事項](#実装推奨事項)
8. [優先度別実装ガイド](#優先度別実装ガイド)

---

## 監査概要

**現在のコード特性:**
- Flask APIフレームワークを使用した温度センサーデータ管理システム
- 4つのエンドポイントで基本的な機能を実装
- エラーハンドリングが基本的
- 入力バリデーションが不十分

**総合評価:** ⚠️ **中程度の改善が必要**
- セキュリティリスク: 3件
- コード冗長性: 2件
- メンテナンス性問題: 4件

---

## セキュリティ面での問題

### 1. **不十分な入力バリデーション** (重大度: 高)

**問題:** 
```python
# 25-26行
temperature = data.get('temperature')
# ...
temperature = float(temperature)  # 33行：エラー処理なし
```

**リスク:**
- `temperature`が`None`の場合、`float(None)`でエラー発生
- `temperature`が非数値の場合、例外発生
- 不正な値（1000°Cなど）も検証されない

**改善案:**
```python
try:
    temperature = float(temperature)
    if not (-50 <= temperature <= 70):  # センサーの物理的範囲
        return jsonify({
            "status": "error",
            "message": "Temperature out of valid range (-50~70°C)"
        }), 400
except (ValueError, TypeError):
    return jsonify({
        "status": "error",
        "message": "Temperature must be a numeric value"
    }), 400
```

---

### 2. **エラーメッセージ情報露出** (重大度: 中)

**問題:**
```python
# 50行、71行、84行など
return jsonify({
    "status": "error",
    "message": str(e)  # ⚠️ スタックトレース詳細が露出
}), 500
```

**リスク:**
- システム内部構造やパス情報がクライアントに露出
- スタックトレース詳細により、攻撃の足がかりになる
- 本番環境では特に危険

**改善案:**
```python
# ログには詳細を保存
logger.error(f"Error processing temperature data: {e}", exc_info=True)

# レスポンスは汎用メッセージ
return jsonify({
    "status": "error",
    "message": "An error occurred processing your request"
}), 500
```

---

### 3. **不安定なJSON解析** (重大度: 中)

**問題:**
```python
# 21行
data = request.get_json(force=True, silent=True)
```

**リスク:**
- `force=True` は不正なContent-Typeも受け入れる
- `silent=True` でエラーが隠される
- 不正なJSONでも強制的にパース試行

**改善案:**
```python
if not request.is_json:
    return jsonify({
        "status": "error",
        "message": "Content-Type must be application/json"
    }), 400

data = request.get_json()  # 正常なJSONのみ解析
if data is None:
    return jsonify({
        "status": "error",
        "message": "Invalid JSON format"
    }), 400
```

---

### 4. **パラメータ値の範囲チェック欠落** (重大度: 中)

**問題:**
```python
# 72行
hours = request.args.get('hours', 24, type=int)
readings = TemperatureQueries.get_range(sensor_id, hours)
```

**リスク:**
- `hours=999999` など大量データ取得でメモリ枯渇（DoS）
- `hours=-1` など不正な値を処理

**改善案:**
```python
hours = request.args.get('hours', 24, type=int)

# 妥当な範囲チェック
if not (1 <= hours <= 720):  # 1時間～30日
    return jsonify({
        "status": "error",
        "message": "Hours must be between 1 and 720"
    }), 400
```

---

## 冗長なコード

### 1. **エラーハンドリングの重複** (重大度: 中)

**問題:** 全エンドポイントで同じパターン

```python
# 48-51行、69-71行、82-85行、104-106行 など
except Exception as e:
    logger.error(f"Error...: {e}")
    return jsonify({"status": "error", "message": str(e)}), 500
```

**影響:** 
- 4回の同じコード繰り返し（DRY原則違反）
- メンテナンスで4箇所修正が必要
- エラー処理ロジック変更時に漏れリスク

**改善案:** 共通ヘルパー関数を作成
```python
def handle_error(error, status_code=500):
    """エラーレスポンスの統一"""
    logger.error(f"{error}", exc_info=True)
    return jsonify({
        "status": "error",
        "message": "An error occurred processing your request"
    }), status_code

# 使用例
except Exception as e:
    return handle_error(e)
```

---

### 2. **バリデーション関数の欠落** (重大度: 中)

**問題:** バリデーション処理が散在

```python
# 25-27行
sensor_id = data.get('device_id') or data.get('sensor_id')
temperature = data.get('temperature')

if not data or not sensor_id or temperature is None:
    logger.warning(f"Invalid data format: {data}")
    return jsonify({...}), 400
```

**改善案:** 共通バリデーション関数
```python
def validate_temperature_request(data):
    """温度データリクエストのバリデーション"""
    sensor_id = data.get('device_id') or data.get('sensor_id')
    temperature = data.get('temperature')
    
    if not sensor_id:
        return False, "Missing sensor_id (device_id or sensor_id)"
    if temperature is None:
        return False, "Missing temperature"
    
    try:
        temp = float(temperature)
        if not (-50 <= temp <= 70):
            return False, "Temperature out of valid range"
        return True, temp
    except (ValueError, TypeError):
        return False, "Temperature must be numeric"
```

---

## 無駄な変数・処理

### 1. **使用されていない `location` 変数** (重大度: 低)

**行:** 36行

```python
# 取得後、ロギングにしか使われていない
location = data.get('location', 'Not set')
logger.info(f"... Location: {location}...")

# 実際にはデータベースに保存されていない
TemperatureQueries.insert_reading(sensor_id, temperature, sensor_name, humidity)
```

**改善:** 使用予定がない場合は削除

```python
# locationを削除
logger.info(f"Temperature saved - Sensor: {sensor_id}, Name: {sensor_name}, Temp: {temperature}°C")
```

---

### 2. **冗長なタイムスタンプ処理** (重大度: 低)

**問題:** 毎回クライアント側で生成

```python
# 45行
"timestamp": datetime.now().isoformat()
```

**改善:** サーバー側で一元化した時刻を使用
```python
"timestamp": datetime.utcnow().isoformat()  # UTC時刻を統一
```

**メリット:** タイムゾーン管理が単純になり、データベース記録と一貫性がとれる

---

### 3. **毎回のモジュールインポート** (重大度: 低)

**行:** 103行

```python
def get_status():
    try:
        import psutil  # ⚠️ 毎回インポート
```

**改善:** モジュール上部に移動
```python
# 1行目付近
import psutil

# get_status()内は直接使用
def get_status():
    try:
        mem = psutil.virtual_memory()
```

---

## 構造とメンテナンス性

### 1. **共通処理の抽出** (重大度: 中)

**問題:**
- 例外処理が4箇所で重複
- バリデーション処理が散在
- レスポンス形式が非統一

**改善:**
```
api.py（改善後の構成）
├── インポート & 初期化
├── ヘルパー関数セクション
│   ├── validate_temperature_request()
│   ├── validate_query_params()
│   └── handle_error()
└── エンドポイント
    ├── /temperature (POST)
    ├── /sensors (GET)
    ├── /temperature/<id> (GET)
    └── /status (GET)
```

---

### 2. **入力検証の一貫性** (重大度: 中)

**現在:**
- `/temperature`: 詳細な検証あり
- `/temperature/<id>`: 範囲チェックなし
- `/status`: 検証なし

**改善:** 全エンドポイントで一貫した検証方針

---

### 3. **ロギングの精度** (重大度: 低)

**問題:**
```python
# 39行
logger.warning(f"Invalid data format: {data}")  # ⚠️ warningは弱い

# 41行
logger.info(f"Data saved...")  # ✅ 良好
```

**改善:**
```python
logger.warning(f"Invalid temperature data received: {data}")  # より具体的
logger.info(f"Temperature data successfully stored: sensor={sensor_id}, temp={temperature}")
```

---

### 4. **エラーレスポンスの統一** (重大度: 低)

**現在:** レスポンス形式がやや異なる

```python
# パターン1
{"status": "error", "message": "...", "device_id": "..."}  # 追加フィールド

# パターン2
{"status": "error", "message": "..."}  # 基本形
```

**改善:** 統一したスキーマを定義
```python
# 成功時
{
    "status": "success",
    "data": {...}
}

# エラー時
{
    "status": "error",
    "message": "...",
    "code": "INVALID_INPUT"  # エラーコード追加
}
```

---

## 改善版コード

### 完全版: api.py（改善後）

```python
"""
ESP32温度センサーAPIエンドポイント
安全性とメンテナンス性を重視した実装
"""

from flask import Blueprint, request, jsonify
from logger import setup_logger
from datetime import datetime
import sys
from pathlib import Path
import psutil

# パス設定
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.queries import TemperatureQueries

logger = setup_logger(__name__)
api_bp = Blueprint('api', __name__)

# ============= 定数 =============
TEMPERATURE_MIN = -50
TEMPERATURE_MAX = 70
HOURS_MIN = 1
HOURS_MAX = 720

# ============= ヘルパー関数 =============

def validate_temperature_request(data):
    """温度データリクエストのバリデーション
    
    Returns:
        tuple: (is_valid: bool, result_or_error: dict or str)
    """
    if not isinstance(data, dict):
        return False, "Request body must be JSON object"
    
    # センサーID取得
    sensor_id = data.get('device_id') or data.get('sensor_id')
    if not sensor_id or not isinstance(sensor_id, str):
        return False, "Missing or invalid sensor_id (device_id or sensor_id)"
    
    # 温度取得
    temperature = data.get('temperature')
    if temperature is None:
        return False, "Missing temperature"
    
    # 温度を数値に変換
    try:
        temperature = float(temperature)
    except (ValueError, TypeError):
        return False, "Temperature must be numeric"
    
    # 温度範囲チェック
    if not (TEMPERATURE_MIN <= temperature <= TEMPERATURE_MAX):
        return False, f"Temperature out of valid range ({TEMPERATURE_MIN}~{TEMPERATURE_MAX}°C)"
    
    # オプションフィールド
    sensor_name = data.get('name') or data.get('sensor_name', 'Unknown')
    humidity = data.get('humidity')
    
    return True, {
        'sensor_id': sensor_id,
        'temperature': temperature,
        'sensor_name': sensor_name,
        'humidity': humidity
    }


def validate_query_params(hours):
    """クエリパラメータのバリデーション
    
    Args:
        hours: 取得時間範囲
        
    Returns:
        tuple: (is_valid: bool, hours_or_error: int or str)
    """
    if not isinstance(hours, int):
        return False, "hours must be integer"
    
    if not (HOURS_MIN <= hours <= HOURS_MAX):
        return False, f"hours must be between {HOURS_MIN} and {HOURS_MAX}"
    
    return True, hours


def handle_error(message, status_code=500):
    """統一されたエラーレスポンス
    
    Args:
        message: ログ用の詳細メッセージ
        status_code: HTTPステータスコード
        
    Returns:
        tuple: (response_json, status_code)
    """
    logger.error(message, exc_info=True)
    return jsonify({
        "status": "error",
        "message": "An error occurred processing your request"
    }), status_code


def success_response(data, status_code=200):
    """統一された成功レスポンス"""
    response = {"status": "success"}
    response.update(data)
    return jsonify(response), status_code


# ============= API エンドポイント =============

@api_bp.route('/temperature', methods=['POST'])
def receive_temperature():
    """ESP32からの温度データ受信
    
    Request JSON:
        {
            "device_id": "sensor_1",  # または sensor_id
            "temperature": 25.5,
            "name": "リビング",
            "humidity": 55.2
        }
    
    Response:
        {
            "status": "success",
            "message": "Data received and stored",
            "device_id": "sensor_1",
            "temperature": 25.5,
            "timestamp": "2025-12-24T12:34:56.789012"
        }
    """
    try:
        # JSONコンテンツタイプ確認
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json"
            }), 400
        
        data = request.get_json()
        if data is None:
            return jsonify({
                "status": "error",
                "message": "Invalid JSON format"
            }), 400
        
        # バリデーション
        is_valid, result = validate_temperature_request(data)
        if not is_valid:
            logger.warning(f"Invalid temperature request: {result}")
            return jsonify({
                "status": "error",
                "message": result
            }), 400
        
        # バリデーション済みデータを展開
        sensor_id = result['sensor_id']
        temperature = result['temperature']
        sensor_name = result['sensor_name']
        humidity = result['humidity']
        
        # データベースに挿入
        TemperatureQueries.insert_reading(sensor_id, temperature, sensor_name, humidity)
        
        logger.info(f"Temperature data saved - Sensor: {sensor_id}, "
                   f"Name: {sensor_name}, Temperature: {temperature}°C, "
                   f"Humidity: {humidity}")
        
        return success_response({
            "message": "Data received and stored",
            "device_id": sensor_id,
            "temperature": temperature,
            "timestamp": datetime.utcnow().isoformat()
        }, 201)

    except Exception as e:
        return handle_error(f"Error processing temperature data: {str(e)}")


@api_bp.route('/sensors', methods=['GET'])
def get_all_sensors():
    """全センサーの最新データを取得
    
    Response:
        {
            "status": "success",
            "sensors": [...],
            "count": 3
        }
    """
    try:
        sensors = TemperatureQueries.get_all_latest()
        
        return success_response({
            "sensors": sensors,
            "count": len(sensors)
        })
        
    except Exception as e:
        return handle_error(f"Error fetching sensors: {str(e)}")


@api_bp.route('/temperature/<sensor_id>', methods=['GET'])
def get_sensor_data(sensor_id):
    """特定センサーのデータを取得
    
    Parameters:
        sensor_id: センサーID（パス）
        hours: データ取得時間範囲 (1~720, デフォルト24)
    
    Response:
        {
            "status": "success",
            "sensor_id": "sensor_1",
            "readings": [...],
            "statistics": {...}
        }
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        
        # クエリパラメータバリデーション
        is_valid, result = validate_query_params(hours)
        if not is_valid:
            logger.warning(f"Invalid query params for sensor {sensor_id}: {result}")
            return jsonify({
                "status": "error",
                "message": result
            }), 400
        
        hours = result
        
        # データベースクエリ
        readings = TemperatureQueries.get_range(sensor_id, hours)
        stats = TemperatureQueries.get_statistics(sensor_id, hours)
        
        logger.info(f"Sensor data retrieved - ID: {sensor_id}, Hours: {hours}, "
                   f"Readings: {len(readings) if readings else 0}")
        
        return success_response({
            "sensor_id": sensor_id,
            "readings": readings,
            "statistics": stats,
            "hours": hours
        })
        
    except Exception as e:
        return handle_error(f"Error fetching sensor data for {sensor_id}: {str(e)}")


@api_bp.route('/status', methods=['GET'])
def get_status():
    """システムステータス取得
    
    Response:
        {
            "status": "online",
            "timestamp": "2025-12-24T12:34:56.789012",
            "connected_sensors": 3,
            "memory_usage_percent": 45.2,
            "disk_usage_percent": 62.1
        }
    """
    try:
        sensors = TemperatureQueries.get_all_latest()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return success_response({
            "timestamp": datetime.utcnow().isoformat(),
            "connected_sensors": len(sensors),
            "memory_usage_percent": round(mem.percent, 1),
            "disk_usage_percent": round(disk.percent, 1)
        })
        
    except Exception as e:
        return handle_error(f"Error getting system status: {str(e)}")
```

---

## 実装推奨事項

### 1. **追加セキュリティ機能** (優先度: 高)

#### a. レート制限

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@limiter.limit("10 per minute")
@api_bp.route('/temperature', methods=['POST'])
def receive_temperature():
    ...
```

#### b. 入力サニタイズ

```python
from bleach import clean

sensor_name = clean(sensor_name, tags=[], strip=True)
```

#### c. CORS設定

```python
from flask_cors import CORS

CORS(api_bp, resources={
    r"/api/*": {
        "origins": ["192.168.1.0/24"],  # 許可するIPレンジ
        "methods": ["GET", "POST"]
    }
})
```

---

### 2. **ロギング&監視強化** (優先度: 中)

```python
# 監査ログ用の専用ロガー
audit_logger = setup_logger("api.audit")

# センシティブ操作は監査ログに
audit_logger.info(f"Data insertion - sensor: {sensor_id}, user: {request.remote_addr}")
```

---

### 3. **テストの追加** (優先度: 高)

```python
# test_api.py
import pytest
from app.routes.api import validate_temperature_request

def test_validate_temperature_valid_data():
    data = {
        "device_id": "sensor_1",
        "temperature": 25.5,
        "name": "test"
    }
    is_valid, result = validate_temperature_request(data)
    assert is_valid is True
    assert result['temperature'] == 25.5

def test_validate_temperature_invalid_range():
    data = {
        "device_id": "sensor_1",
        "temperature": 100
    }
    is_valid, result = validate_temperature_request(data)
    assert is_valid is False
    assert "out of valid range" in result
```

---

### 4. **API仕様書の作成** (優先度: 中)

```python
# Swagger/OpenAPI仕様
from flasgger import Swagger

swagger = Swagger(app)

@api_bp.route('/temperature', methods=['POST'])
def receive_temperature():
    """
    ---
    tags:
      - Temperature
    summary: ESP32から温度データを受信
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - device_id
            - temperature
          properties:
            device_id:
              type: string
              example: "sensor_1"
            temperature:
              type: number
              example: 25.5
    responses:
      201:
        description: データが正常に保存されました
      400:
        description: 入力エラー
    """
    ...
```

---

### 5. **例外クラスの定義** (優先度: 中)

```python
# exceptions.py
class TemperatureOutOfRangeError(ValueError):
    """温度が有効範囲外の場合"""
    pass

class InvalidSensorIdError(ValueError):
    """無効なセンサーID"""
    pass

# 使用例
if not (TEMPERATURE_MIN <= temperature <= TEMPERATURE_MAX):
    raise TemperatureOutOfRangeError(f"Temperature {temperature} out of range")
```

---

## 優先度別実装ガイド

### Phase 1: 即座に実装（セキュリティリスク）
- [ ] 温度値の範囲チェック追加
- [ ] JSON Content-Type検証追加
- [ ] エラーメッセージの情報露出削除
- [ ] hoursパラメータの範囲チェック追加

**所要時間:** 1-2時間  
**影響:** セキュリティリスク軽減

---

### Phase 2: 短期実装（保守性向上）
- [ ] ヘルパー関数（validate, handle_error）作成
- [ ] 冗長なエラーハンドリング削除
- [ ] location変数削除
- [ ] psutilインポート移動

**所要時間:** 2-3時間  
**影響:** メンテナンス性大幅向上

---

### Phase 3: 中期実装（機能強化）
- [ ] ユニットテスト作成
- [ ] レート制限実装
- [ ] API仕様書（Swagger）作成
- [ ] 例外クラス定義

**所要時間:** 4-6時間  
**影響:** 本番運用対応

---

### Phase 4: 長期実装（運用機能）
- [ ] 詳細な監査ログシステム
- [ ] メトリクス収集（Prometheus等）
- [ ] アラート設定
- [ ] キャッシング機能追加

**所要時間:** 8-12時間  
**影響:** 運用効率化

---

## チェックリスト

```
セキュリティ
[ ] 温度値の範囲チェック
[ ] JSON Content-Type検証
[ ] エラーメッセージの安全化
[ ] hoursパラメータ検証
[ ] レート制限設定

コード品質
[ ] 共通ヘルパー関数化
[ ] 冗長コード削除
[ ] 未使用変数削除
[ ] 一貫したログレベル
[ ] 統一されたレスポンス形式

メンテナンス性
[ ] 関数の責任を単一化
[ ] 共通処理を上部に集約
[ ] コメント/ドキュメント追加
[ ] エラーコード定義
[ ] 設定値の定数化

テスト・ドキュメント
[ ] ユニットテスト作成
[ ] 統合テスト作成
[ ] API仕様書作成
[ ] README更新
[ ] 例外タイプ定義
```

---

## 参考資料

- [OWASP Top 10 - API Security](https://owasp.org/www-project-api-security/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [RESTful API Design Guidelines](https://restfulapi.net/)

---

**監査完了日:** 2025年12月24日  
**次回監査予定:** 実装完了後、機能テスト時
