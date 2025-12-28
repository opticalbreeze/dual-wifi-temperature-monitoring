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
        sensor_id = data.get('device_id') or data.get('sensor_id')
        temperature = data.get('temperature')
        
        logger.info(f"バリデーション - sensor_id: {sensor_id}, temperature: {temperature}")

        if not data or not sensor_id or temperature is None:
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
            
            logger.info(f"DB挿入開始 - sensor_id: {sensor_id}, temp: {temperature}, name: {sensor_name}, humidity: {humidity}")
            
            result = TemperatureQueries.insert_reading(sensor_id, temperature, sensor_name, humidity)
            logger.info(f"DB挿入結果: {result}")
            
            logger.info(f"✅ データ保存成功 - Device: {sensor_id}, Name: {sensor_name}, Location: {location}, Temp: {temperature}°C")
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
        readings = TemperatureQueries.get_range(sensor_id, hours)
        stats = TemperatureQueries.get_statistics(sensor_id, hours)

        return jsonify({
            "status": "success",
            "sensor_id": sensor_id,
            "readings": readings,
            "statistics": stats
        })
    except Exception as e:
        logger.error(f"Error fetching sensor data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/status', methods=['GET'])
def get_status():
    """システムステータスを取得"""
    try:
        import psutil
        mem = psutil.virtual_memory()

        sensors = TemperatureQueries.get_all_latest()

        return jsonify({
            "status": "online",
            "timestamp": str(datetime.now()),
            "connected_sensors": len(sensors),
            "memory_usage_percent": mem.percent,
            "disk_usage_percent": psutil.disk_usage('/').percent
        })
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

