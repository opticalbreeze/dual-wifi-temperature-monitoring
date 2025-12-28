#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta, timezone

db_path = "/home/raspberry/temperature_monitoring/temperature_server/data/temperature.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 最新レコードのタイムスタンプを確認
cursor.execute("SELECT id, sensor_id, temperature, timestamp FROM temperatures ORDER BY timestamp DESC LIMIT 1")
latest = cursor.fetchone()

print(f"Latest record timestamp: {latest['timestamp']}")
print(f"Current time (system): {datetime.now().isoformat()}")
print(f"Current time (JST):    {datetime.now(timezone(timedelta(hours=9))).isoformat()}")

# タイムスタンプをパース
ts_str = latest['timestamp']
try:
    ts_parsed = datetime.fromisoformat(ts_str)
    print(f"\nParsed timestamp: {ts_parsed}")
    print(f"Parsed timestamp (UTC): {ts_parsed.replace(tzinfo=timezone.utc)}")
    
    # JST として解釈した場合
    ts_jst = datetime.fromisoformat(ts_str).replace(tzinfo=timezone(timedelta(hours=9)))
    print(f"As JST: {ts_jst}")
    
except Exception as e:
    print(f"Parse error: {e}")

# テーブル定義を確認
cursor.execute("PRAGMA table_info(temperatures)")
columns = cursor.fetchall()
print("\nTable schema:")
for col in columns:
    print(f"  {col['name']}: {col['type']}")

conn.close()
