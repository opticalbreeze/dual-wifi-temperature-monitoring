"""
temperature_server/database/models.py
SQLite スキーマ定義
"""

import sqlite3
from pathlib import Path
from config import Config

DB_PATH = Path(Config.DATA_DIR) / "temperature.db"

def init_database():
    """データベーステーブルを初期化"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 温度データテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temperatures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT NOT NULL,
            sensor_name TEXT,
            temperature REAL NOT NULL,
            humidity REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # インデックス作成（クエリ高速化）
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sensor_timestamp 
        ON temperatures(sensor_id, timestamp DESC)
    """)
    
    # WiFi 接続履歴
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wifi_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ssid TEXT NOT NULL,
            connection_status TEXT,
            signal_strength INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # シスログ
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT,
            module TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def get_connection():
    """スレッドセーフなDB接続を取得"""
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
