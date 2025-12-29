"""
temperature_server/services/serial_reader.py
USB/シリアル経由でESP32からの温度データを受信

システム構成:
- ラズパイにUSB接続されたESP32がマスター
- このESP32はESP-NOWで複数のESP32/ESP8266からデータを受信
- ラズパイはUSB/シリアル経由でこのESP32から温度データを取得
- 受信データをSQLiteに格納
"""

import serial
import threading
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from config import Config
from database.queries import TemperatureQueries

logger = logging.getLogger(__name__)


class SerialReader:
    """USB/シリアル経由でESP32からデータを受信"""
    
    def __init__(self, port=None, baudrate=115200, timeout=1):
        """
        初期化
        
        Args:
            port (str): シリアルポート（例: '/dev/ttyUSB0'）
                       Noneの場合は自動検出
            baudrate (int): ボーレート（デフォルト: 115200）
            timeout (float): 読み込みタイムアウト（秒）
        """
        self.port = port or self._auto_detect_port()
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        self.is_running = False
        self.reader_thread = None
        
        logger.info(f"SerialReader initialized: port={self.port}, baudrate={self.baudrate}")
    
    def _auto_detect_port(self):
        """
        利用可能なシリアルポートを自動検出
        
        /dev/ttyUSB* または /dev/ttyACM* から検出
        複数ある場合は最初のものを使用
        
        Returns:
            str: ポートパス（見つからない場合はNone）
        """
        try:
            import glob
            # Linux: /dev/ttyUSB* (CH340等) または /dev/ttyACM* (STM32等)
            ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
            if ports:
                detected_port = ports[0]
                logger.info(f"Auto-detected serial port: {detected_port}")
                return detected_port
            
            logger.warning("No serial port found. Please check USB connection.")
            return None
        except Exception as e:
            logger.error(f"Error auto-detecting serial port: {e}")
            return None
    
    def connect(self):
        """
        シリアルポートを開く
        
        Returns:
            bool: 成功時True、失敗時False
        """
        try:
            if not self.port:
                logger.error("Serial port not specified and auto-detection failed")
                return False
            
            # シリアルポートを開く
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            
            logger.info(f"Connected to {self.port} at {self.baudrate} baud")
            return True
        
        except serial.SerialException as e:
            logger.error(f"Failed to connect to serial port: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during serial connection: {e}")
            return False
    
    def disconnect(self):
        """シリアルポートを閉じる"""
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
                logger.info("Disconnected from serial port")
        except Exception as e:
            logger.error(f"Error closing serial port: {e}")
    
    def start(self):
        """
        シリアル受信スレッドを開始
        
        バックグラウンドスレッドで常時リッスンを開始
        """
        if self.is_running:
            logger.warning("Serial reader is already running")
            return
        
        if not self.connect():
            logger.error("Cannot start serial reader without connection")
            return
        
        self.is_running = True
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.reader_thread.start()
        logger.info("Serial reader thread started")
    
    def stop(self):
        """シリアル受信スレッドを停止"""
        self.is_running = False
        if self.reader_thread:
            self.reader_thread.join(timeout=5)
        self.disconnect()
        logger.info("Serial reader stopped")
    
    def _read_loop(self):
        """
        シリアル読み込みループ（バックグラウンドスレッド）
        
        常時ESP32からのデータを監視し、
        受信したら _process_data() で処理
        """
        buffer = ""
        
        while self.is_running:
            try:
                # シリアルポートから1バイト読み込み
                if self.serial_conn.in_waiting > 0:
                    byte = self.serial_conn.read(1).decode('utf-8', errors='ignore')
                    buffer += byte
                    
                    # 改行で1行が完成
                    if byte == '\n':
                        line = buffer.strip()
                        buffer = ""
                        
                        if line:
                            self._process_line(line)
                else:
                    time.sleep(0.01)  # CPU負荷軽減
            
            except UnicodeDecodeError:
                # 不正なUTF-8はスキップ
                buffer = ""
            except Exception as e:
                logger.error(f"Error in read loop: {e}")
                time.sleep(1)
    
    def _process_line(self, line):
        """
        受信した1行をパース・処理
        
        フォーマット例:
        {"device_id":"ESP32_MAIN","sensors":[{"sensor_id":"ESP32_PROT_01","temp":22.5,"humidity":45.2},...]}
        
        Args:
            line (str): 受信した行文字列
        """
        try:
            # JSON パース
            data = json.loads(line)
            logger.debug(f"Received JSON: {data}")
            
            # データ処理
            self._process_json_data(data)
        
        except json.JSONDecodeError as e:
            # JSON形式以外のテキスト（デバッグ出力等）はスキップ
            logger.debug(f"Non-JSON line: {line}")
        except Exception as e:
            logger.error(f"Error processing line: {e}")
    
    def _process_json_data(self, data):
        """
        受信したJSONデータを処理・DB保存
        
        ESP32から送信されるデータ構造:
        {
            "device_id": "ESP32_MAIN",           # マスターESP32のID
            "sensors": [                          # ESP-NOWで受信したセンサーデータ
                {
                    "sensor_id": "ESP32_PROT_01",
                    "sensor_name": "DS18B20-01",
                    "temp": 22.5,
                    "humidity": 45.2,
                    "rssi": -45                    # 信号強度（オプション）
                },
                ...
            ]
        }
        
        Args:
            data (dict): パースされたJSONデータ
        """
        try:
            # マスターデバイスID取得
            master_device_id = data.get('device_id')
            if not master_device_id:
                logger.warning("Missing 'device_id' in received data")
                return
            
            # センサーデータの配列を取得
            sensors = data.get('sensors', [])
            if not isinstance(sensors, list):
                logger.warning(f"Invalid 'sensors' format: {type(sensors)}")
                return
            
            # 各センサーのデータをDB保存
            saved_count = 0
            for sensor in sensors:
                if self._save_sensor_data(sensor, master_device_id):
                    saved_count += 1
            
            if saved_count > 0:
                logger.info(f"[Serial] Saved {saved_count} sensor readings from {master_device_id}")
        
        except Exception as e:
            logger.error(f"Error processing JSON data: {e}", exc_info=True)
    
    def _save_sensor_data(self, sensor, master_id):
        """
        センサーデータをDBに保存
        
        Args:
            sensor (dict): センサーデータ
            master_id (str): マスターESP32のID
        
        Returns:
            bool: 保存成功時True
        """
        try:
            # 必須フィールド取得
            sensor_id = sensor.get('sensor_id')
            temperature = sensor.get('temp') or sensor.get('temperature')
            
            if not sensor_id or temperature is None:
                logger.warning(f"Missing required fields in sensor data: {sensor}")
                return False
            
            # オプショナルフィールド
            sensor_name = sensor.get('sensor_name', 'Unknown')
            humidity = sensor.get('humidity')
            rssi = sensor.get('rssi')  # 信号強度（情報用）
            
            # DBに挿入
            TemperatureQueries.insert_reading(
                sensor_id=sensor_id,
                temperature=float(temperature),
                sensor_name=sensor_name,
                humidity=float(humidity) if humidity is not None else None
            )
            
            logger.debug(
                f"[Serial] Saved: {sensor_id} = {temperature}°C "
                f"(via {master_id}, name={sensor_name}, humidity={humidity}, rssi={rssi})"
            )
            return True
        
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid data type in sensor: {sensor}, error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error saving sensor data: {e}", exc_info=True)
            return False


def create_serial_reader(config_obj=None):
    """
    SerialReaderのファクトリ関数
    
    Args:
        config_obj: Config オブジェクト（デフォルト: Config）
    
    Returns:
        SerialReader: 初期化済みのSerialReaderインスタンス
    """
    if config_obj is None:
        config_obj = Config
    
    reader = SerialReader(
        port=getattr(config_obj, 'SERIAL_PORT', None),
        baudrate=getattr(config_obj, 'SERIAL_BAUDRATE', 115200),
        timeout=getattr(config_obj, 'SERIAL_TIMEOUT', 1)
    )
    return reader
