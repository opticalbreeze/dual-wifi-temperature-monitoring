#!/usr/bin/env python3
"""
temperature_server/run.py
アプリケーション起動スクリプト
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
from database.models import init_database
from logger import setup_logger
from app import create_app

logger = setup_logger('main')

def main():
    """アプリケーション起動"""
    try:
        # データベース初期化
        logger.info("Initializing database...")
        init_database()
        
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

if __name__ == '__main__':
    main()
