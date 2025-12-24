#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
from pathlib import Path
import threading
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

DB_PATH = Path('/home/raspberry/temperature_server/temperature_data.db')
DB_LOCK = threading.Lock()

def init_database():
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS sensors (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT UNIQUE NOT NULL, name TEXT NOT NULL, location TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
            cursor.execute('CREATE TABLE IF NOT EXISTS temperature_data (id INTEGER PRIMARY KEY AUTOINCREMENT, sensor_id INTEGER NOT NULL, temperature REAL NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(sensor_id) REFERENCES sensors(id))')
            conn.commit()
            logger.info("Database initialized")

def get_sensor_id(device_id, name="Unknown", location=""):
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM sensors WHERE device_id = ?', (device_id,))
            result = cursor.fetchone()
            if result:
                return result[0]
            cursor.execute('INSERT INTO sensors (device_id, name, location) VALUES (?, ?, ?)', (device_id, name, location))
            conn.commit()
            return cursor.lastrowid

@app.route('/api/temperature', methods=['POST'])
def receive_temperature():
    try:
        data = request.get_json()
        device_id = data.get('device_id', 'unknown')
        name = data.get('name', 'Unknown')
        location = data.get('location', '')
        temperature = float(data.get('temperature', 0))
        sensor_id = get_sensor_id(device_id, name, location)
        with DB_LOCK:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO temperature_data (sensor_id, temperature) VALUES (?, ?)', (sensor_id, temperature))
                conn.commit()
        logger.info(f"Received: {device_id} = {temperature}C")
        return jsonify({'status': 'ok', 'sensor_id': sensor_id}), 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT id, device_id, name, location FROM sensors')
            sensors = [dict(row) for row in cursor.fetchall()]
    return jsonify(sensors), 200

@app.route('/api/temperature/<int:sensor_id>', methods=['GET'])
def get_temperature_history(sensor_id):
    hours = request.args.get('hours', 24, type=int)
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT temperature, timestamp FROM temperature_data WHERE sensor_id = ? AND timestamp > datetime("now", "-" || ? || " hours") ORDER BY timestamp ASC', (sensor_id, hours))
            data = [dict(row) for row in cursor.fetchall()]
    return jsonify(data), 200

@app.route('/api/temperature/all-latest', methods=['GET'])
def get_all_latest():
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT s.id, s.device_id, s.name, s.location, t.temperature, t.timestamp FROM sensors s LEFT JOIN temperature_data t ON s.id = t.sensor_id WHERE t.id IS NULL OR t.id = (SELECT id FROM temperature_data WHERE sensor_id = s.id ORDER BY timestamp DESC LIMIT 1)')
            results = [dict(row) for row in cursor.fetchall()]
    return jsonify(results), 200

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/system/status', methods=['GET'])
def system_status():
    """システム状態診断エンドポイント"""
    import subprocess
    try:
        results = {}
        
        # hostapd状態
        try:
            hostapd_status = subprocess.run(['systemctl', 'is-active', 'hostapd'], capture_output=True, text=True, timeout=5)
            results['hostapd'] = hostapd_status.stdout.strip()
        except:
            results['hostapd'] = 'error'
        
        # dnsmasq状態
        try:
            dnsmasq_status = subprocess.run(['systemctl', 'is-active', 'dnsmasq'], capture_output=True, text=True, timeout=5)
            results['dnsmasq'] = dnsmasq_status.stdout.strip()
        except:
            results['dnsmasq'] = 'error'
        
        # wlan1インターフェース
        try:
            ifconfig = subprocess.run(['ifconfig', 'wlan1'], capture_output=True, text=True, timeout=5)
            results['wlan1'] = ifconfig.stdout if ifconfig.returncode == 0 else 'not found'
        except:
            results['wlan1'] = 'error'
        
        # iwconfig wlan1
        try:
            iwconfig = subprocess.run(['iwconfig', 'wlan1'], capture_output=True, text=True, timeout=5)
            results['iwconfig'] = iwconfig.stdout if iwconfig.returncode == 0 else 'not found'
        except:
            results['iwconfig'] = 'error'
        
        # hostapd_cli status
        try:
            hostapd_cli = subprocess.run(['hostapd_cli', 'status'], capture_output=True, text=True, timeout=5)
            results['hostapd_cli'] = hostapd_cli.stdout if hostapd_cli.returncode == 0 else hostapd_cli.stderr
        except:
            results['hostapd_cli'] = 'command not available'
        
        # 最新ジャーナルログ
        try:
            journal_hostapd = subprocess.run(['journalctl', '-u', 'hostapd', '-n', '20', '--no-pager'], capture_output=True, text=True, timeout=5)
            results['hostapd_logs'] = journal_hostapd.stdout
        except:
            results['hostapd_logs'] = 'error'
        
        return jsonify(results), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
