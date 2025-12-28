#!/usr/bin/env python3
import sqlite3

db_path = "/home/raspberry/temperature_monitoring/temperature_server/data/temperature.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("SELECT id, sensor_id, timestamp FROM temperatures ORDER BY id DESC LIMIT 10")
rows = c.fetchall()

print("Latest 10 records in DB:")
for row in rows:
    print(f"  ID: {row[0]}, Sensor: {row[1]}, Time: {row[2]}")

conn.close()
