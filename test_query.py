#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

# Raspberry Pi のデータベースパス
db_path = "/home/raspberry/temperature_monitoring/temperature_server/data/temperature.db"

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. 全レコード数
    cursor.execute("SELECT COUNT(*) as count FROM temperatures")
    total = cursor.fetchone()
    print(f"Total records: {total['count']}")
    
    # 2. ESP32_PROT_01 の全レコード
    cursor.execute("SELECT * FROM temperatures WHERE sensor_id='ESP32_PROT_01' ORDER BY timestamp DESC")
    prot01_rows = cursor.fetchall()
    print(f"\nESP32_PROT_01 records: {len(prot01_rows)}")
    for row in prot01_rows[:3]:
        print(f"  ID: {row['id']}, Temp: {row['temperature']}, Time: {row['timestamp']}")
    
    # 3. 修正版クエリテスト（0.5時間 = 30分）
    jst_now = datetime.now(JST)
    since_jst = (jst_now - timedelta(hours=0.5))
    since_str = since_jst.strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"\nJST Now: {jst_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Since (30min ago): {since_str}")
    
    cursor.execute("""
        SELECT * FROM temperatures 
        WHERE sensor_id = ? AND timestamp > ?
        ORDER BY timestamp ASC
    """, ('ESP32_PROT_01', since_str))
    
    recent_rows = cursor.fetchall()
    print(f"Records in last 30min: {len(recent_rows)}")
    for row in recent_rows:
        print(f"  ID: {row['id']}, Temp: {row['temperature']}, Time: {row['timestamp']}")
    
    conn.close()

except Exception as e:
    print(f"Error: {e}")
