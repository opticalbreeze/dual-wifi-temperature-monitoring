#!/usr/bin/env python3
"""
temperature_server/run.py
アプリケーション起動スクリプト

起動時の処理:
1. データベース初期化
2. シリアルリーダー起動（USB/Serial経由のESP32データ受信）
3. Flask Webサーバー起動
"""

import sys
from pathlib import Path
import os

# 環境変数設定
os.environ.setdefault('FLASK_ENV', 'production')

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import Config
from database.models import init_database, migrate_add_rssi_battery
from logger import setup_logger
from app import create_app
from services.serial_reader import create_serial_reader

logger = setup_logger('main')

# ===== メイン処理 =====
def main():
    """アプリケーション起動"""
    logger.info("=" * 80)
    logger.info("🚀 Temperature Server 起動")
    logger.info("=" * 80)
    
    # 1. データベース初期化
    logger.info("📊 データベースを初期化中...")
    init_database()
    migrate_add_rssi_battery()  # 既存DBにカラムを追加
    logger.info("✓ データベース初期化完了")

# グローバル変数（シリアルリーダー）
serial_reader = None


def start_serial_reader():
    """
    シリアルリーダーを起動（USB/Serial経由のESP32データ受信）
    
    この機能により以下が可能になります:
    - ラズパイにUSB接続したESP32からシリアル経由でデータを受信
    - 受信したESP32はESP-NOWで複数のESP32/ESP8266からデータを受信
    - すべてのデータが自動的にSQLiteに格納される
    """
    global serial_reader
    
    if not Config.SERIAL_ENABLED:
        logger.info("Serial reader is disabled (SERIAL_ENABLED=False)")
        return
    
    try:
        logger.info("Starting serial reader...")
        serial_reader = create_serial_reader(Config)
        
        if serial_reader.port is None:
            logger.warning("No serial port found. Check USB connection.")
            serial_reader = None
            return
        
        serial_reader.start()
        logger.info(f"✅ Serial reader started on {serial_reader.port}")
        
    except Exception as e:
        logger.error(f"Failed to start serial reader: {e}", exc_info=True)
        serial_reader = None


def stop_serial_reader():
    """シリアルリーダーを停止"""
    global serial_reader
    
    if serial_reader:
        try:
            serial_reader.stop()
            logger.info("Serial reader stopped")
        except Exception as e:
            logger.error(f"Error stopping serial reader: {e}")


def main():
    """アプリケーション起動"""
    try:
        # データベース初期化
        logger.info("Initializing database...")
        init_database()
        
        # シリアルリーダー起動
        start_serial_reader()
        
        # Flask アプリを作成
        logger.info("Creating Flask application...")
        app = create_app()
        
        # 起動
        logger.info(f"Starting server on {Config.FLASK_HOST}:{Config.FLASK_PORT}")
        print(f"\n🚀 Temperature Server Started!")
        print(f"📊 Dashboard: http://{Config.FLASK_HOST}:{Config.FLASK_PORT}/")
        print(f"📡 API: http://{Config.FLASK_HOST}:{Config.FLASK_PORT}/api/")
        print(f"🎥 Stream: http://{Config.FLASK_HOST}:{Config.FLASK_PORT}/stream")
        print(f"⚙️  Management: http://{Config.FLASK_HOST}:{Config.FLASK_PORT}/management\n")
        
        if Config.SERIAL_ENABLED:
            if serial_reader:
                print(f"📶 Serial Reader: {serial_reader.port} @ {serial_reader.baudrate} baud\n")
            else:
                print(f"⚠️  Serial Reader: Not connected (check USB connection)\n")
        
        app.run(
            host=Config.FLASK_HOST,
            port=Config.FLASK_PORT,
            debug=Config.FLASK_DEBUG,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        # クリーンアップ
        stop_serial_reader()


if __name__ == '__main__':
    main()
