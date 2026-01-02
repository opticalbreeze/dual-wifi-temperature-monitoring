"""
temperature_server/app/routes/api_improved.py
改善されたAPIルート（エラーハンドリング統合版）
"""

from flask import Blueprint, request, jsonify
from logger import setup_logger
from datetime import datetime
import sys
from pathlib import Path

# パス設定
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.queries import TemperatureQueries, SystemLogQueries
from utils.exceptions import ValidationException, DatabaseException, SensorException
from utils.validators import (
    validate_temperature_request,
    validate_hours,
    validate_sensor_ids
)
from utils.error_handler import handle_errors
from utils.request_tracing import trace_request, log_with_request_id
from utils.health_check import HealthChecker

logger = setup_logger(__name__)
api_bp = Blueprint('api', __name__)


@api_bp.route('/temperature', methods=['POST'])
@trace_request
@handle_errors
def receive_temperature():
    """ESP32からの温度データ受信（改善版）"""
    log_with_request_id("温度データ受信リクエスト", level='info')
    
    # JSONをパース
    data = request.get_json(force=True, silent=True)
    
    # バリデーション
    is_valid, error_msg, validated_data = validate_temperature_request(data)
    if not is_valid:
        raise ValidationException(
            message=error_msg,
            field='request_data',
            details={'raw_data': str(data)[:200]}  # 最初の200文字のみ
        )
    
    # データベースに挿入
    try:
        TemperatureQueries.insert_reading(
            validated_data['sensor_id'],
            validated_data['temperature'],
            validated_data['sensor_name'],
            validated_data['humidity'],
            validated_data['rssi'],
            validated_data['battery_mode']
        )
        
        log_with_request_id(
            f"データ保存成功 - Sensor: {validated_data['sensor_id']}, "
            f"Temp: {validated_data['temperature']}°C",
            level='info'
        )
        
    except Exception as db_error:
        raise DatabaseException(
            message=f"データベースへの保存に失敗しました: {str(db_error)}",
            operation='insert_reading',
            details={'sensor_id': validated_data['sensor_id']}
        ) from db_error
    
    from utils.request_tracing import get_request_id
    
    return jsonify({
        "status": "success",
        "message": "Data received and stored",
        "device_id": validated_data['sensor_id'],
        "temperature": validated_data['temperature'],
        "rssi": validated_data['rssi'],
        "battery_mode": validated_data['battery_mode'],
        "timestamp": datetime.now().isoformat(),
        "request_id": get_request_id()
    }), 201


@api_bp.route('/sensors', methods=['GET'])
@trace_request
@handle_errors
def get_all_sensors():
    """全センサーの最新データを取得（改善版）"""
    log_with_request_id("全センサー取得リクエスト", level='info')
    
    try:
        sensors = TemperatureQueries.get_all_latest()
        log_with_request_id(f"センサー数: {len(sensors)}", level='info')
    except Exception as e:
        raise DatabaseException(
            message=f"センサーデータの取得に失敗しました: {str(e)}",
            operation='get_all_latest'
        ) from e
    
    return jsonify({
        "status": "success",
        "sensors": sensors,
        "count": len(sensors)
    })


@api_bp.route('/temperature/<sensor_id>', methods=['GET'])
@trace_request
@handle_errors
def get_sensor_data(sensor_id):
    """特定センサーのデータを取得（改善版）"""
    # センサーIDのバリデーション
    is_valid, error_msg = validate_sensor_id(sensor_id)
    if not is_valid:
        raise SensorException(
            message=error_msg,
            sensor_id=sensor_id
        )
    
    # 時間範囲のバリデーション
    hours_raw = request.args.get('hours', 24, type=float)
    is_valid, error_msg, hours = validate_hours(hours_raw)
    if not is_valid:
        raise ValidationException(
            message=error_msg,
            field='hours'
        )
    
    log_with_request_id(
        f"センサーデータ取得 - Sensor: {sensor_id}, Hours: {hours}",
        level='debug'
    )
    
    try:
        readings = TemperatureQueries.get_range(sensor_id, hours)
        stats = TemperatureQueries.get_statistics(sensor_id, hours)
    except Exception as e:
        raise DatabaseException(
            message=f"センサーデータの取得に失敗しました: {str(e)}",
            operation='get_range',
            details={'sensor_id': sensor_id, 'hours': hours}
        ) from e
    
    return jsonify({
        "status": "success",
        "sensor_id": sensor_id,
        "readings": readings,
        "statistics": stats
    })


@api_bp.route('/temperature/batch', methods=['POST'])
@trace_request
@handle_errors
def get_temperature_batch():
    """複数センサーのデータを一括取得（改善版）"""
    data = request.get_json()
    
    if not data:
        raise ValidationException(
            message="リクエストデータが空です",
            field='request_body'
        )
    
    # センサーIDリストのバリデーション
    sensor_ids = data.get('sensor_ids', [])
    is_valid, error_msg, validated_ids = validate_sensor_ids(sensor_ids)
    if not is_valid:
        raise ValidationException(
            message=error_msg,
            field='sensor_ids'
        )
    
    # 時間範囲のバリデーション
    hours_raw = data.get('hours', 24)
    is_valid, error_msg, hours = validate_hours(hours_raw)
    if not is_valid:
        raise ValidationException(
            message=error_msg,
            field='hours'
        )
    
    log_with_request_id(
        f"バッチ取得 - Sensors: {len(validated_ids)}, Hours: {hours}",
        level='debug'
    )
    
    try:
        # バッチ取得
        readings_map = TemperatureQueries.get_range_batch(validated_ids, hours)
        
        # 各センサーの統計も取得
        results = {}
        for sensor_id in validated_ids:
            readings = readings_map.get(sensor_id, [])
            stats = TemperatureQueries.get_statistics(sensor_id, hours)
            results[sensor_id] = {
                "readings": readings,
                "statistics": stats
            }
    except Exception as e:
        raise DatabaseException(
            message=f"バッチデータ取得に失敗しました: {str(e)}",
            operation='get_range_batch',
            details={'sensor_ids': validated_ids, 'hours': hours}
        ) from e
    
    return jsonify({
        "status": "success",
        "data": results,
        "count": len(results)
    })


@api_bp.route('/health', methods=['GET'])
@trace_request
@handle_errors
def health_check():
    """システムヘルスチェック"""
    health_status = HealthChecker.check_all()
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    
    return jsonify(health_status), status_code


@api_bp.route('/status', methods=['GET'])
@trace_request
@handle_errors
def get_status():
    """システムステータスを取得（改善版）"""
    try:
        import psutil
        mem = psutil.virtual_memory()
        uptime = datetime.now().timestamp() - psutil.Process(1).create_time()
        
        sensors = TemperatureQueries.get_all_latest()
        
        return jsonify({
            "status": "online",
            "timestamp": str(datetime.now()),
            "connected_sensors": len(sensors),
            "memory_percent": round(mem.percent, 1),
            "disk_percent": round(psutil.disk_usage('/').percent, 1),
            "uptime_seconds": int(uptime)
        })
    except ImportError:
        raise ValidationException(
            message="psutilがインストールされていません",
            details={'package': 'psutil'}
        )
    except Exception as e:
        raise DatabaseException(
            message=f"ステータス取得に失敗しました: {str(e)}",
            operation='get_status'
        ) from e


@api_bp.route('/logs', methods=['GET'])
@trace_request
@handle_errors
def get_logs():
    """ログを取得（改善版）"""
    limit = request.args.get('limit', 50, type=int)
    
    if limit < 1 or limit > 1000:
        raise ValidationException(
            message="limitは1～1000の範囲で指定してください",
            field='limit',
            details={'provided': limit}
        )
    
    try:
        logs = SystemLogQueries.get_recent_logs(limit)
    except Exception as e:
        raise DatabaseException(
            message=f"ログ取得に失敗しました: {str(e)}",
            operation='get_recent_logs'
        ) from e
    
    return jsonify({
        "status": "success",
        "logs": logs,
        "count": len(logs)
    })


@api_bp.route('/delete-old-data', methods=['POST'])
@trace_request
@handle_errors
def delete_old_data():
    """指定日数以前のデータを削除（改善版）"""
    data = request.get_json()
    days_old = data.get('days_old', 30) if data else 30
    
    if days_old < 1:
        raise ValidationException(
            message="days_oldは1以上である必要があります",
            field='days_old',
            details={'provided': days_old}
        )
    
    log_with_request_id(f"古いデータ削除開始 - Days: {days_old}", level='info')
    
    try:
        deleted_count = TemperatureQueries.delete_old_records(days_old)
    except Exception as e:
        raise DatabaseException(
            message=f"データ削除に失敗しました: {str(e)}",
            operation='delete_old_records',
            details={'days_old': days_old}
        ) from e
    
    return jsonify({
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"{deleted_count}件のデータを削除しました"
    })


@api_bp.route('/delete-test-sensors', methods=['POST'])
@trace_request
@handle_errors
def delete_test_sensors():
    """テストセンサーのデータを削除（改善版）"""
    log_with_request_id("テストセンサーデータ削除開始", level='info')
    
    try:
        deleted_count = TemperatureQueries.delete_test_sensors()
    except Exception as e:
        raise DatabaseException(
            message=f"テストセンサーデータ削除に失敗しました: {str(e)}",
            operation='delete_test_sensors'
        ) from e
    
    return jsonify({
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"テストセンサーデータ {deleted_count}件を削除しました"
    })

