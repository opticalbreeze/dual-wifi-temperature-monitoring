import os
from pathlib import Path

# ディレクトリパス
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / 'logs'
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'temperature_data.db'

class Config:
    """アプリケーション設定クラス"""
    
    # Flask 設定
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    FLASK_HOST = '0.0.0.0'
    FLASK_PORT = 5000
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # ディレクトリ
    BASE_DIR = BASE_DIR
    LOGS_DIR = LOGS_DIR
    DATA_DIR = DATA_DIR
    DB_PATH = DB_PATH
    
    # WiFi 設定
    AP_SSID = 'RaspberryPi_Temperature'
    AP_PASSWORD = 'RaspberryPi2025'
    AP_INTERFACE = 'wlan1'  # USB WiFi (AP モード) - ESP32から接続
    STATION_INTERFACE = 'wlan0'  # オンボードWiFi (Station モード) - インターネット接続
    AP_IP = '192.168.4.1'
    AP_SUBNET = '192.168.4.0/24'
    AP_DHCP_START = '192.168.4.2'
    AP_DHCP_END = '192.168.4.254'
    
    # メモリ管理
    MEMORY_THRESHOLD = 80  # %
    MEMORY_CHECK_INTERVAL = 300  # 秒
    
    # WiFi 管理
    WIFI_CHECK_INTERVAL = 600  # 秒
    WIFI_RETRY_ATTEMPTS = 3
    WIFI_RETRY_DELAY = 10  # 秒
    
    # ビデオストリーミング
    AVAILABLE_RESOLUTIONS = {
        '360p': (640, 360, 24),
        '720p': (1280, 720, 24),
        '1080p': (1920, 1080, 30)
    }
    DEFAULT_RESOLUTION = '720p'
    
    # ロギング
    LOG_MAX_BYTES = 10485760  # 10MB
    LOG_BACKUP_COUNT = 5
    LOG_RETENTION_DAYS = 7
    
    # Tailscale
    TAILSCALE_ENABLED = os.getenv('TAILSCALE_ENABLED', 'False').lower() == 'true'
    TAILSCALE_AUTH_KEY = os.getenv('TAILSCALE_AUTH_KEY', '')

# ディレクトリ作成
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
