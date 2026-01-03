from flask import Blueprint, request, jsonify
from logger import setup_logger
from datetime import datetime
import sys
import uuid
import subprocess
from pathlib import Path

# パス設定
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.queries import TemperatureQueries, SystemLogQueries

logger = setup_logger(__name__)
api_bp = Blueprint('api', __name__)

@api_bp.route('/temperature', methods=['POST'])
def receive_temperature():
    """ESP32からの温度データ受信"""
    request_id = str(uuid.uuid4())[:8]
    
    try:
        logger.info(f"[{request_id}] POST /api/temperature リクエスト受信")
        logger.info(f"[{request_id}] IP: {request.remote_addr}")
        
        # 生リクエストボディを取得
        raw_body = request.get_data(as_text=True)
        logger.info(f"[{request_id}] Content-Type: {request.content_type}")
        logger.info(f"[{request_id}] 生リクエストボディ: {raw_body}")
        
        # JSONをパース
        data = request.get_json(force=True, silent=True)
        if not data:
            logger.warning(f"[{request_id}] ❌ JSONデコード失敗: {raw_body}")
            return jsonify({
                "status": "error",
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid JSON format",
                "request_id": request_id
            }), 400
        
        logger.info(f"[{request_id}] JSONデコード成功: {data}")
        
        # バリデーション
        sensor_id = data.get('device_id') or data.get('sensor_id')
        temperature = data.get('temperature') or data.get('temp')
        
        if not sensor_id or temperature is None:
            logger.warning(f"[{request_id}] ❌ バリデーション失敗: 必須フィールド不足")
            return jsonify({
                "status": "error",
                "error_code": "VALIDATION_ERROR",
                "message": "Missing required fields: device_id/sensor_id, temperature",
                "request_id": request_id
            }), 400
        
        # データベースに挿入
        try:
            temperature = float(temperature)
            sensor_name = data.get('name') or data.get('sensor_name', 'Unknown')
            humidity = data.get('humidity')
            rssi = data.get('rssi')
            battery_mode = data.get('battery_mode', False)
            connection_type = 'wifi_ap' if rssi is not None else 'esp_now'
            
            logger.info(f"[{request_id}] DB挿入開始 - sensor_id: {sensor_id}, temp: {temperature}°C")
            
            TemperatureQueries.insert_reading(
                sensor_id, temperature, sensor_name, humidity, rssi, battery_mode, connection_type
            )
            
            logger.info(f"[{request_id}] ✅ データ保存成功")
            
            return jsonify({
                "status": "success",
                "message": "Data received and stored",
                "device_id": sensor_id,
                "temperature": temperature,
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }), 201
            
        except Exception as db_error:
            logger.error(f"[{request_id}] ❌ DB挿入エラー: {db_error}", exc_info=True)
            return jsonify({
                "status": "error",
                "error_code": "DATABASE_ERROR",
                "message": f"Failed to insert data: {str(db_error)}",
                "request_id": request_id
            }), 500

    except Exception as e:
        logger.error(f"[{request_id}] ❌ 予期しないエラー: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error_code": "INTERNAL_ERROR",
            "message": "Internal server error",
            "request_id": request_id
        }), 500

@api_bp.route('/sensors', methods=['GET'])
def get_all_sensors():
    """全センサーの最新データを取得"""
    request_id = str(uuid.uuid4())[:8]
    
    try:
        logger.info(f"[{request_id}] GET /api/sensors リクエスト")
        sensors = TemperatureQueries.get_all_latest()
        logger.info(f"[{request_id}] {len(sensors)}台のセンサーを取得")
        
        return jsonify({
            "status": "success",
            "sensors": sensors,
            "count": len(sensors),
            "request_id": request_id
        })
    
    except Exception as e:
        logger.error(f"[{request_id}] ❌ センサー取得エラー: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error_code": "SENSOR_ERROR",
            "message": "Failed to fetch sensors",
            "request_id": request_id
        }), 500

@api_bp.route('/temperature/<sensor_id>', methods=['GET'])
def get_sensor_data(sensor_id):
    """特定センサーのデータを取得"""
    request_id = str(uuid.uuid4())[:8]
    
    try:
        hours = request.args.get('hours', 24, type=float)
        
        logger.info(f"[{request_id}] GET /api/temperature/{sensor_id} - hours={hours}")
        
        # hours のバリデーション
        if hours <= 0 or hours > 8760:
            logger.warning(f"[{request_id}] ❌ hours バリデーション失敗: {hours}")
            return jsonify({
                "status": "error",
                "error_code": "VALIDATION_ERROR",
                "message": "hours must be between 0 and 8760",
                "request_id": request_id
            }), 400
        
        readings = TemperatureQueries.get_range(sensor_id, hours)
        stats = TemperatureQueries.get_statistics(sensor_id, hours)
        
        logger.info(f"[{request_id}] {len(readings)}件のレコードを取得")

        return jsonify({
            "status": "success",
            "sensor_id": sensor_id,
            "readings": readings,
            "statistics": stats,
            "request_id": request_id
        })
    
    except Exception as e:
        logger.error(f"[{request_id}] ❌ センサーデータ取得エラー: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error_code": "SENSOR_ERROR",
            "message": f"Failed to fetch sensor data: {sensor_id}",
            "request_id": request_id
        }), 500

@api_bp.route('/status', methods=['GET'])
def get_status():
    """システムステータスを取得"""
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
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/logs', methods=['GET'])
def get_logs():
    """ログを取得"""
    try:
        limit = request.args.get('limit', 50, type=int)
        logs = SystemLogQueries.get_recent_logs(limit)
        return jsonify({
            "status": "success",
            "logs": logs,
            "count": len(logs)
        })
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/delete-old-data', methods=['POST'])
def delete_old_data():
    """指定日数以前のデータを削除"""
    try:
        data = request.get_json()
        days_old = data.get('days_old', 30)
        logger.info(f"Deleting data older than {days_old} days")
        
        deleted_count = TemperatureQueries.delete_old_records(days_old)
        
        return jsonify({
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"{deleted_count}件のデータを削除しました"
        })
    except Exception as e:
        logger.error(f"Error deleting old data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/delete-test-sensors', methods=['POST'])
def delete_test_sensors():
    """テストセンサーのデータを削除"""
    try:
        deleted_count = TemperatureQueries.delete_test_sensors()
        logger.info(f"Deleted {deleted_count} test sensor records")
        
        return jsonify({
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"テストセンサーデータ {deleted_count}件を削除しました"
        })
    except Exception as e:
        logger.error(f"Error deleting test sensors: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/temperature/batch', methods=['POST'])
def get_temperature_batch():
    """複数センサーのデータを一括取得（高速化・間引き対応）"""
    try:
        data = request.get_json()
        if not data or 'sensor_ids' not in data:
            return jsonify({'status': 'error', 'message': 'sensor_idsが指定されていません'}), 400
        
        sensor_ids = data.get('sensor_ids', [])
        hours = float(data.get('hours', 24))
        max_points = int(data.get('max_points', 500))  # クライアント側で指定可能
        
        if not isinstance(sensor_ids, list) or len(sensor_ids) == 0:
            return jsonify({'status': 'error', 'message': 'sensor_idsは空でないリストである必要があります'}), 400
        
        logger.debug(f"GET /api/temperature/batch - sensor_ids={sensor_ids}, hours={hours}, max_points={max_points}")
        
        # バッチ取得（サーバー側で間引き）
        readings_map = TemperatureQueries.get_range_batch(sensor_ids, hours)
        
        # 各センサーの統計も取得
        results = {}
        total_original_points = 0
        total_downsampled_points = 0
        
        for sensor_id in sensor_ids:
            readings = readings_map.get(sensor_id, [])
            stats = TemperatureQueries.get_statistics(sensor_id, hours)
            results[sensor_id] = {
                "readings": readings,
                "statistics": stats
            }
            total_downsampled_points += len(readings)
        
        logger.debug(f"GET /api/temperature/batch - Found data for {len(results)} sensors, {total_downsampled_points} total points")
        
        return jsonify({
            "status": "success",
            "data": results,
            "count": len(results),
            "total_points": total_downsampled_points
        })
    except Exception as e:
        logger.error(f"Error fetching batch temperature data: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


def check_ap_status():
    """WiFi APの稼働状況を確認"""
    try:
        # hostapd と dnsmasq の両方が起動しているか確認
        result = subprocess.run(
            ["/usr/bin/pgrep", "hostapd"],
            capture_output=True,
            timeout=5
        )
        hostapd_running = result.returncode == 0
        
        result = subprocess.run(
            ["/usr/bin/pgrep", "dnsmasq"],
            capture_output=True,
            timeout=5
        )
        dnsmasq_running = result.returncode == 0
        
        logger.debug(f"AP status check: hostapd={hostapd_running}, dnsmasq={dnsmasq_running}")
        return hostapd_running and dnsmasq_running
    except Exception as e:
        logger.warning(f"AP status check failed: {e}")
        return False


@api_bp.route('/status/ap', methods=['GET'])
def get_ap_status():
    """WiFi AP稼働状況を返す"""
    try:
        ap_running = check_ap_status()
        return jsonify({
            "status": "success",
            "ap_running": ap_running,
            "message": "WiFi AP 稼働中" if ap_running else "WiFi AP 停止中"
        })
    except Exception as e:
        logger.error(f"Error checking AP status: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@api_bp.route('/dashboard/combined', methods=['POST'])
def get_dashboard_combined():
    """ダッシュボード用統合エンドポイント（センサーリスト＋グラフデータを一度に取得）"""
    request_id = str(uuid.uuid4())[:8]
    
    try:
        data = request.get_json() or {}
        sensor_ids = data.get('sensor_ids', [])
        hours = float(data.get('hours', 6))  # デフォルト6時間
        
        logger.info(f"[{request_id}] GET /api/dashboard/combined - sensor_ids={sensor_ids}, hours={hours}")
        
        # センサーリストを取得
        sensors = TemperatureQueries.get_all_sensors()
        
        # グラフデータを取得
        if sensor_ids and len(sensor_ids) > 0:
            readings_map = TemperatureQueries.get_range_batch(sensor_ids, hours)
        else:
            readings_map = {}
        
        # レスポンス構築
        response = {
            "status": "success",
            "request_id": request_id,
            "sensors": sensors,
            "data": readings_map,
            "hours": hours,
            "count": len(sensors)
        }
        
        logger.info(f"[{request_id}] Dashboard combined data ready - {len(sensors)} sensors, {sum(len(v.get('readings', [])) for v in readings_map.values())} data points")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"[{request_id}] Error fetching dashboard combined data: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "request_id": request_id
        }), 500

