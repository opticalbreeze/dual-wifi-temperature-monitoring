"""
ESP32温度センサーAPIエンドポイント
安全性とメンテナンス性を重視した実装
"""

from flask import Blueprint, request, jsonify
from logger import setup_logger
import sys
from pathlib import Path
import pytz
import psutil

# パス設定
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.queries import TemperatureQueries, SystemLogQueries, get_jst_now
from app.exceptions import (
    TemperatureOutOfRangeError,
    InvalidSensorIdError,
    InvalidTemperatureError,
    InvalidHoursParameterError,
    InvalidJSONError,
    DatabaseError
)

# JSTタイムゾーン
JST = pytz.timezone('Asia/Tokyo')

logger = setup_logger(__name__)
api_bp = Blueprint('api', __name__)

# ============= 定数 =============
TEMPERATURE_MIN = -50
TEMPERATURE_MAX = 70
HOURS_MIN = 0.5
HOURS_MAX = 720

# ============= ヘルパー関数 =============

def validate_temperature_request(data):
    """温度データリクエストのバリデーション
    
    Returns:
        tuple: (is_valid: bool, result_or_error: dict or Exception)
    """
    if not isinstance(data, dict):
        return False, InvalidJSONError("Request body must be JSON object")
    
    # センサーID取得
    sensor_id = data.get('device_id') or data.get('sensor_id')
    if not sensor_id or not isinstance(sensor_id, str):
        return False, InvalidSensorIdError(sensor_id)
    
    # 温度取得
    temperature = data.get('temperature')
    if temperature is None:
        return False, InvalidTemperatureError()
    
    # 温度を数値に変換
    try:
        temperature = float(temperature)
    except (ValueError, TypeError):
        return False, InvalidTemperatureError(temperature)
    
    # 温度範囲チェック
    if not (TEMPERATURE_MIN <= temperature <= TEMPERATURE_MAX):
        return False, TemperatureOutOfRangeError(temperature, TEMPERATURE_MIN, TEMPERATURE_MAX)
    
    # オプションフィールド
    sensor_name = data.get('name') or data.get('sensor_name', 'Unknown')
    humidity = data.get('humidity')
    
    return True, {
        'sensor_id': sensor_id,
        'temperature': temperature,
        'sensor_name': sensor_name,
        'humidity': humidity
    }


def validate_hours_param(hours):
    """クエリパラメータのバリデーション
    
    Args:
        hours: 取得時間範囲
        
    Returns:
        tuple: (is_valid: bool, hours_or_error: float or Exception)
    """
    if not isinstance(hours, (int, float)):
        return False, InvalidHoursParameterError(hours, HOURS_MIN, HOURS_MAX)
    
    if not (HOURS_MIN <= hours <= HOURS_MAX):
        return False, InvalidHoursParameterError(hours, HOURS_MIN, HOURS_MAX)
    
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
            "timestamp": "2025-12-24T12:34:56.789012+09:00"
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
            error = InvalidJSONError("Invalid JSON format")
            logger.warning(f"Invalid JSON request: {str(error)}")
            return jsonify({
                "status": "error",
                "message": str(error)
            }), 400
        
        # バリデーション
        is_valid, result = validate_temperature_request(data)
        if not is_valid:
            # resultはExceptionオブジェクト
            error_message = str(result)
            logger.warning(f"Invalid temperature request: {error_message}")
            return jsonify({
                "status": "error",
                "message": error_message
            }), 400
        
        # バリデーション済みデータを展開
        sensor_id = result['sensor_id']
        temperature = result['temperature']
        sensor_name = result['sensor_name']
        humidity = result['humidity']
        
        # データベースに挿入
        TemperatureQueries.insert_reading(sensor_id, temperature, sensor_name, humidity)
        
        # JST時刻を取得
        jst_now = get_jst_now()
        logger.info(f"Temperature data saved - Sensor: {sensor_id}, "
                   f"Name: {sensor_name}, Temperature: {temperature}°C, "
                   f"Humidity: {humidity}")
        
        return success_response({
            "message": "Data received and stored",
            "device_id": sensor_id,
            "temperature": temperature,
            "timestamp": jst_now.isoformat()
        }, 201)

    except (TemperatureOutOfRangeError, InvalidSensorIdError, InvalidTemperatureError, InvalidJSONError) as e:
        # バリデーションエラーは400を返す
        logger.warning(f"Validation error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except DatabaseError as e:
        # データベースエラーは500を返す
        return handle_error(f"Database error: {str(e)}", 500)
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
        
    except DatabaseError as e:
        return handle_error(f"Database error: {str(e)}", 500)
    except Exception as e:
        return handle_error(f"Error fetching sensors: {str(e)}")


@api_bp.route('/temperature/<sensor_id>', methods=['GET'])
def get_sensor_data(sensor_id):
    """特定センサーのデータを取得
    
    Parameters:
        sensor_id: センサーID（パス）
        hours: データ取得時間範囲 (0.5~720, デフォルト24)
    
    Response:
        {
            "status": "success",
            "sensor_id": "sensor_1",
            "readings": [...],
            "statistics": {...}
        }
    """
    try:
        hours = request.args.get('hours', 24, type=float)
        
        # クエリパラメータバリデーション
        is_valid, result = validate_hours_param(hours)
        if not is_valid:
            # resultはExceptionオブジェクト
            error_message = str(result)
            logger.warning(f"Invalid query params for sensor {sensor_id}: {error_message}")
            return jsonify({
                "status": "error",
                "message": error_message
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
            "statistics": stats
        })
        
    except InvalidHoursParameterError as e:
        logger.warning(f"Invalid hours parameter: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except DatabaseError as e:
        return handle_error(f"Database error: {str(e)}", 500)
    except Exception as e:
        return handle_error(f"Error fetching sensor data for {sensor_id}: {str(e)}")


@api_bp.route('/status', methods=['GET'])
def get_status():
    """システムステータス取得
    
    Response:
        {
            "status": "online",
            "timestamp": "2025-12-24T12:34:56.789012+09:00",
            "connected_sensors": 3,
            "memory_usage_percent": 45.2,
            "disk_usage_percent": 62.1
        }
    """
    try:
        sensors = TemperatureQueries.get_all_latest()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        jst_now = get_jst_now()
        return success_response({
            "status": "online",
            "timestamp": jst_now.isoformat(),
            "connected_sensors": len(sensors),
            "memory_usage_percent": round(mem.percent, 1),
            "disk_usage_percent": round(disk.percent, 1)
        })
        
    except Exception as e:
        return handle_error(f"Error getting system status: {str(e)}")
