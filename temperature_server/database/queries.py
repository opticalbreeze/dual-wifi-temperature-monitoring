"""
temperature_server/database/queries.py
データベースクエリ操作（スレッドセーフ）
"""

import threading
from datetime import datetime, timedelta, timezone
from database.models import get_connection

db_lock = threading.Lock()

# JST タイムゾーン定義
JST = timezone(timedelta(hours=9))

class TemperatureQueries:
    
    @staticmethod
    def insert_reading(sensor_id, temperature, sensor_name=None, humidity=None):
        """温度データを挿入（ローカルタイムゾーン）"""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            # ローカル時刻で現在時刻を取得（Raspberry Pi は Asia/Tokyo に設定済み）
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                INSERT INTO temperatures 
                (sensor_id, sensor_name, temperature, humidity, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (sensor_id, sensor_name, temperature, humidity, now))
            conn.commit()
            conn.close()
    
    @staticmethod
    def get_latest_reading(sensor_id):
        """センサーの最新データを取得"""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM temperatures 
                WHERE sensor_id = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (sensor_id,))
            result = cursor.fetchone()
            conn.close()
            if result:
                return dict(result)
            return None
    
    @staticmethod
    def get_all_latest():
        """全センサーの最新データを取得"""
        import logging
        db_logger = logging.getLogger('database.queries')
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            
            # 全センサーの最新データを1つのクエリで取得（デッドロック回避）
            cursor.execute("""
                SELECT t1.* FROM temperatures t1
                WHERE t1.id = (
                    SELECT MAX(id) FROM temperatures t2 
                    WHERE t2.sensor_id = t1.sensor_id
                )
                ORDER BY t1.sensor_id
            """)
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            conn.close()
            
            db_logger.info(f"get_all_latest: Found {len(results)} sensors")
            for data in results:
                db_logger.debug(f"get_all_latest: Sensor: {data.get('sensor_id')}, Temp: {data.get('temperature')}, Time: {data.get('timestamp')}")
            
            return results
    
    @staticmethod
    def get_range(sensor_id, hours=24):
        """指定時間範囲のデータを取得（ローカルタイムゾーン）"""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            # ローカル時刻から指定時間前の時刻を計算（Raspberry Pi は Asia/Tokyo に設定済み）
            # JST時刻で計算
            since = (datetime.now(JST) - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT * FROM temperatures 
                WHERE sensor_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """, (sensor_id, since))
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            conn.close()
            return results
    
    @staticmethod
    def get_statistics(sensor_id, hours=24):
        """温度統計を計算（ローカルタイムゾーン）"""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            # ローカル時刻から指定時間前の時刻を計算（JST時刻で計算）
            since = (datetime.now(JST) - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT 
                    COUNT(*) as count,
                    AVG(temperature) as avg_temp,
                    MIN(temperature) as min_temp,
                    MAX(temperature) as max_temp
                FROM temperatures 
                WHERE sensor_id = ? AND timestamp >= ?
            """, (sensor_id, since))
            result = cursor.fetchone()
            conn.close()
            if result:
                return dict(result)
            return {}

class SystemLogQueries:
    
    @staticmethod
    def insert_log(level, module, message):
        """システムログを挿入"""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_logs (level, module, message)
                VALUES (?, ?, ?)
            """, (level, module, message))
            conn.commit()
            conn.close()
    
    @staticmethod
    def get_recent_logs(limit=100):
        """最近のログを取得"""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM system_logs 
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            conn.close()
            return results
    
    @staticmethod
    def cleanup_old_logs(days=7):
        """古いログを削除"""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            since = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute("DELETE FROM system_logs WHERE timestamp < ?", (since,))
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted

