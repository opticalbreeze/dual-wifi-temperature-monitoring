#!/usr/bin/env python3
"""テストセンサーデータを削除"""
import sqlite3
import os

# 正しいパスを指定
db_path = '/home/raspberry/temperature_monitoring/temperature_server/data/temperature.db'
if not os.path.exists(db_path):
    print(f"データベースが見つかりません: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()

# テストセンサーIDを確認
c.execute("SELECT DISTINCT sensor_id FROM temperature_readings WHERE sensor_id LIKE '%TEST%'")
test_sensors = c.fetchall()
print('削除対象センサー:', test_sensors)

# テストセンサーのデータを削除
c.execute("DELETE FROM temperature_readings WHERE sensor_id LIKE '%TEST%'")
deleted_count = c.rowcount
print(f'削除件数: {deleted_count}')

conn.commit()
conn.close()
print('✓ テストデータを削除しました')
