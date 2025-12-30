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
            rssi INTEGER,
            battery_mode INTEGER DEFAULT 0,
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
    
    # 温度アラートテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temperature_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT NOT NULL,
            sensor_name TEXT,
            temperature REAL NOT NULL,
            min_threshold REAL NOT NULL,
            max_threshold REAL NOT NULL,
            alert_type TEXT NOT NULL,
            message TEXT,
            acknowledged INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # アラートインデックス作成
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alert_sensor_timestamp 
        ON temperature_alerts(sensor_id, timestamp DESC)
    """)
    
    # 設定テーブル（温度範囲など）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # デフォルト設定を挿入（存在しない場合のみ）
    cursor.execute("""
        INSERT OR IGNORE INTO settings (key, value, description) 
        VALUES 
        ('temperature_min', '5.0', '最低温度閾値（℃）'),
        ('temperature_max', '40.0', '最高温度閾値（℃）'),
        ('alert_enabled', '1', 'アラート機能有効/無効（1=有効, 0=無効）')
    """)
    
    conn.commit()
    conn.close()

def migrate_add_rssi_battery():
    """既存のテーブルに rssi と battery_mode カラムを追加"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # rssi カラム追加
        cursor.execute("ALTER TABLE temperatures ADD COLUMN rssi INTEGER")
        print("✓ rssi カラムを追加しました")
    except sqlite3.OperationalError:
        print("※ rssi カラムは既に存在します")
    
    try:
        # battery_mode カラム追加
        cursor.execute("ALTER TABLE temperatures ADD COLUMN battery_mode INTEGER DEFAULT 0")
        print("✓ battery_mode カラムを追加しました")
    except sqlite3.OperationalError:
        print("※ battery_mode カラムは既に存在します")
    
    conn.commit()
    conn.close()

def get_connection():
    """スレッドセーフなDB接続を取得"""
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
