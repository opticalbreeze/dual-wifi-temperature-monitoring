"""
temperature_server/app/routes/wifi.py
WiFi 管理 API エンドポイント
"""

from flask import Blueprint, request, jsonify
from logger import setup_logger
import sys
from pathlib import Path

# パス設定
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.wifi_manager import WiFiManager

logger = setup_logger(__name__)
wifi_bp = Blueprint('wifi', __name__, url_prefix='/wifi')

# グローバル WiFi マネージャー
wifi_manager = WiFiManager()

@wifi_bp.route('/status', methods=['GET'])
def wifi_status():
    """WiFi ステータスを取得"""
    try:
        ap_status = wifi_manager.get_ap_status()
        station_status = wifi_manager.get_station_status()
        
        return jsonify({
            "status": "success",
            "ap": ap_status,
            "station": station_status
        })
    except Exception as e:
        logger.error(f"Error getting WiFi status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@wifi_bp.route('/health', methods=['GET'])
def wifi_health():
    """WiFi ヘルスチェック"""
    try:
        health = wifi_manager.health_check()
        return jsonify(health)
    except Exception as e:
        logger.error(f"Error checking WiFi health: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@wifi_bp.route('/scan', methods=['GET'])
def scan_networks():
    """利用可能なネットワークをスキャン"""
    try:
        networks = wifi_manager.scan_networks()
        return jsonify({
            "status": "success",
            "networks": networks,
            "count": len(networks)
        })
    except Exception as e:
        logger.error(f"Error scanning networks: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@wifi_bp.route('/connect', methods=['POST'])
def connect():
    """WiFi ネットワークに接続"""
    try:
        data = request.get_json(force=True, silent=True)
        
        if not data or 'ssid' not in data or 'password' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required fields: ssid, password"
            }), 400
        
        ssid = data.get('ssid')
        password = data.get('password')
        timeout = data.get('timeout', 30)
        
        success = wifi_manager.connect_to_network(ssid, password, timeout)
        
        return jsonify({
            "status": "success" if success else "error",
            "ssid": ssid,
            "message": f"Connected to {ssid}" if success else f"Failed to connect to {ssid}"
        })
    except Exception as e:
        logger.error(f"Error connecting to WiFi: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@wifi_bp.route('/disconnect', methods=['POST'])
def disconnect():
    """WiFi ネットワークから切断"""
    try:
        success = wifi_manager.disconnect_network()
        
        return jsonify({
            "status": "success" if success else "error",
            "message": "Disconnected" if success else "Failed to disconnect"
        })
    except Exception as e:
        logger.error(f"Error disconnecting WiFi: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@wifi_bp.route('/ap/start', methods=['POST'])
def start_ap():
    """AP を開始"""
    try:
        success = wifi_manager.start_ap()
        
        return jsonify({
            "status": "success" if success else "error",
            "message": "AP started" if success else "Failed to start AP"
        })
    except Exception as e:
        logger.error(f"Error starting AP: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@wifi_bp.route('/ap/stop', methods=['POST'])
def stop_ap():
    """AP を停止"""
    try:
        success = wifi_manager.stop_ap()
        
        return jsonify({
            "status": "success" if success else "error",
            "message": "AP stopped" if success else "Failed to stop AP"
        })
    except Exception as e:
        logger.error(f"Error stopping AP: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@wifi_bp.route('/ap/restart', methods=['POST'])
def restart_ap():
    """AP を再起動"""
    try:
        success = wifi_manager.restart_ap()
        
        return jsonify({
            "status": "success" if success else "error",
            "message": "AP restarted" if success else "Failed to restart AP"
        })
    except Exception as e:
        logger.error(f"Error restarting AP: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
