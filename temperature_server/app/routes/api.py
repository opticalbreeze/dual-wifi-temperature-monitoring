from flask import Blueprint, request, jsonify
from logger import setup_logger
from datetime import datetime
import sys
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
    try:
        # ============================================================
        logger.info("[POST /api/temperature] リクエスト受信")
        logger.info(f"IP: {request.remote_addr}")
        logger.info(f"リクエストヘッダー: {dict(request.headers)}")
        
        # 生リクエストボディを取得
        raw_body = request.get_data(as_text=True)
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Content-Length: {request.content_length}")
        logger.info(f"生リクエストボディ: {raw_body}")
        
        # JSONをパース
        data = request.get_json(force=True, silent=True)
        logger.info(f"JSONデコード結果: {data}")

        # バリデーション（device_id または sensor_id をサポート）
        if not data:
            logger.warning(f"❌ バリデーション失敗 - JSONデコード失敗またはデータがNone: {raw_body}")
            return jsonify({
                "status": "error",
                "message": "Invalid JSON format"
            }), 400
        
        sensor_id = data.get('device_id') or data.get('sensor_id')
        temperature = data.get('temperature') or data.get('temp')
        
        logger.info(f"バリデーション - sensor_id: {sensor_id}, temperature: {temperature}")

        if not sensor_id or temperature is None:
            logger.warning(f"❌ バリデーション失敗 - Invalid data format: {data}")
            return jsonify({
                "status": "error",
                "message": "Missing required fields: device_id/sensor_id, temperature"
            }), 400

        # データベースに挿入
        try:
            temperature = float(temperature)
            sensor_name = data.get('name') or data.get('sensor_name', 'Unknown')
            location = data.get('location', 'Not set')
            humidity = data.get('humidity')
            rssi = data.get('rssi')  # WiFi信号強度
            battery_mode = data.get('battery_mode', False)  # バッテリーモード
            
            logger.info(f"DB挿入開始 - sensor_id: {sensor_id}, temp: {temperature}, name: {sensor_name}, humidity: {humidity}, rssi: {rssi}, battery_mode: {battery_mode}")
            
            TemperatureQueries.insert_reading(sensor_id, temperature, sensor_name, humidity, rssi, battery_mode)
            
            logger.info(f"✅ データ保存成功 - Device: {sensor_id}, Name: {sensor_name}, Location: {location}, Temp: {temperature}°C, RSSI: {rssi}dBm, Battery: {battery_mode}")
            logger.info("============================================================")
        except Exception as db_error:
            logger.error(f"❌ DB挿入エラー: {db_error}", exc_info=True)
            logger.info("============================================================")
            raise

        return jsonify({
            "status": "success",
            "message": "Data received and stored",
            "device_id": sensor_id,
            "temperature": temperature,
            "rssi": rssi,
            "battery_mode": battery_mode,
            "timestamp": datetime.now().isoformat()
        }), 201

    except Exception as e:
        logger.error(f"❌ エラー - Error processing temperature data: {e}", exc_info=True)
        logger.info("============================================================")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api_bp.route('/sensors', methods=['GET'])
def get_all_sensors():
    """全センサーの最新データを取得"""
    try:
        logger.info("GET /api/sensors - Request received")
        sensors = TemperatureQueries.get_all_latest()
        logger.info(f"GET /api/sensors - Found {len(sensors)} sensors")
        if sensors:
            for sensor in sensors:
                logger.debug(f"GET /api/sensors - Sensor: {sensor.get('sensor_id')}, Temp: {sensor.get('temperature')}, Time: {sensor.get('timestamp')}")
        else:
            logger.warning("GET /api/sensors - No sensors found")
        response = {
            "status": "success",
            "sensors": sensors,
            "count": len(sensors)
        }
        logger.info(f"GET /api/sensors - Response: {len(sensors)} sensors")
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching sensors: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/temperature/<sensor_id>', methods=['GET'])
def get_sensor_data(sensor_id):
    """特定センサーのデータを取得"""
    try:
        hours = request.args.get('hours', 24, type=float)  # float対応（0.5時間の30分に対応）
        logger.debug(f"GET /api/temperature/{sensor_id} - hours={hours}")
        readings = TemperatureQueries.get_range(sensor_id, hours)
        stats = TemperatureQueries.get_statistics(sensor_id, hours)
        
        logger.debug(f"GET /api/temperature/{sensor_id} - Found {len(readings)} readings")

        return jsonify({
            "status": "success",
            "sensor_id": sensor_id,
            "readings": readings,
            "statistics": stats
        })
    except Exception as e:
        logger.error(f"Error fetching sensor data: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

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
    """複数センサーのデータを一括取得（高速化）"""
    try:
        data = request.get_json()
        if not data or 'sensor_ids' not in data:
            return jsonify({'status': 'error', 'message': 'sensor_idsが指定されていません'}), 400
        
        sensor_ids = data.get('sensor_ids', [])
        hours = data.get('hours', 24, type=float)
        
        if not isinstance(sensor_ids, list) or len(sensor_ids) == 0:
            return jsonify({'status': 'error', 'message': 'sensor_idsは空でないリストである必要があります'}), 400
        
        logger.debug(f"GET /api/temperature/batch - sensor_ids={sensor_ids}, hours={hours}")
        
        # バッチ取得
        readings_map = TemperatureQueries.get_range_batch(sensor_ids, hours)
        
        # 各センサーの統計も取得
        results = {}
        for sensor_id in sensor_ids:
            readings = readings_map.get(sensor_id, [])
            stats = TemperatureQueries.get_statistics(sensor_id, hours)
            results[sensor_id] = {
                "readings": readings,
                "statistics": stats
            }
        
        logger.debug(f"GET /api/temperature/batch - Found data for {len(results)} sensors")
        
        return jsonify({
            "status": "success",
            "data": results,
            "count": len(results)
        })
    except Exception as e:
        logger.error(f"Error fetching batch temperature data: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

