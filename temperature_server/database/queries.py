"""
temperature_server/database/queries.py
データベースクエリ操作（スレッドセーフ）
"""

import threading
from datetime import datetime, timedelta
import pytz
from database.models import get_connection

db_lock = threading.Lock()

# JSTタイムゾーン
JST = pytz.timezone('Asia/Tokyo')

def get_jst_now():
    """現在時刻をJSTで取得"""
    return datetime.now(JST)

class TemperatureQueries:
    @staticmethod
    def insert_reading(sensor_id, temperature, sensor_name=None, humidity=None):
        """温度データを挿入（JST時刻で保存）"""
        import logging
        logger = logging.getLogger(__name__)
        try:
            with db_lock:
                conn = get_connection()
                cursor = conn.cursor()
                # JST時刻を明示的に取得して保存
                jst_now = get_jst_now()
                cursor.execute("""
                    INSERT INTO temperatures
                    (sensor_id, sensor_name, temperature, humidity, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (sensor_id, sensor_name, temperature, humidity, jst_now.strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                logger.info(f"Data inserted: sensor_id={sensor_id}, temp={temperature}, timestamp={jst_now.isoformat()}, rowid={cursor.lastrowid}")
                conn.close()
        except Exception as e:
            logger.error(f"Failed to insert data: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_latest_reading(sensor_id):
        """センサーの最新データを取得（JST時刻をISO形式で返す）"""
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
                row_dict = dict(result)
                # timestampをISO形式に変換（JSTとして扱う）
                if row_dict.get('timestamp'):
                    timestamp_str = row_dict['timestamp']
                    if isinstance(timestamp_str, str):
                        if 'T' not in timestamp_str:
                            timestamp_str = timestamp_str.replace(' ', 'T')
                        if '+' not in timestamp_str and 'Z' not in timestamp_str:
                            timestamp_str = timestamp_str + '+09:00'
                        row_dict['timestamp'] = timestamp_str
                return row_dict
            return None
    
    @staticmethod
    def get_all_latest():
        """全センサーの最新データを取得（JST時刻をISO形式で返す）"""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
        
            # すべてのセンサーの最新データを1つのクエリで取得
            cursor.execute("""
                SELECT t1.*
                FROM temperatures t1
                INNER JOIN (
                    SELECT sensor_id, MAX(id) as max_id
                    FROM temperatures
                    GROUP BY sensor_id
                ) t2 ON t1.sensor_id = t2.sensor_id AND t1.id = t2.max_id
                ORDER BY t1.timestamp DESC
            """)
        
        results = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # timestampをISO形式に変換（JSTとして扱う）
            if row_dict.get('timestamp'):
                # SQLiteから取得した時刻文字列をJSTとして解釈してISO形式に変換
                timestamp_str = row_dict['timestamp']
                if isinstance(timestamp_str, str):
                    # "2025-12-24 09:15:40" 形式を "2025-12-24T09:15:40+09:00" に変換
                    if 'T' not in timestamp_str:
                        timestamp_str = timestamp_str.replace(' ', 'T')
                    if '+' not in timestamp_str and 'Z' not in timestamp_str:
                        timestamp_str = timestamp_str + '+09:00'
                    row_dict['timestamp'] = timestamp_str
            results.append(row_dict)
        conn.close()
        return results
    
    @staticmethod
    def get_range(sensor_id, hours=24):
        """指定時間範囲のデータを取得（JST時刻をISO形式で返す）"""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            # JST時刻で計算（hoursはfloatでもOK）
            since = (get_jst_now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT * FROM temperatures 
                WHERE sensor_id = ? AND timestamp > ?
                ORDER BY timestamp ASC
            """, (sensor_id, since))  # ASCに変更（時系列順）
            results = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                # timestampをISO形式に変換（JSTとして扱う）
                if row_dict.get('timestamp'):
                    timestamp_str = row_dict['timestamp']
                    if isinstance(timestamp_str, str):
                        if 'T' not in timestamp_str:
                            timestamp_str = timestamp_str.replace(' ', 'T')
                        if '+' not in timestamp_str and 'Z' not in timestamp_str:
                            timestamp_str = timestamp_str + '+09:00'
                        row_dict['timestamp'] = timestamp_str
                results.append(row_dict)
            conn.close()
            return results
    
    @staticmethod
    def get_statistics(sensor_id, hours=24):
        """温度統計を計算"""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            # JST時刻で計算（hoursはfloatでもOK）
            since = (get_jst_now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT 
                    COUNT(*) as count,
                    AVG(temperature) as avg_temp,
                    MIN(temperature) as min_temp,
                    MAX(temperature) as max_temp
                FROM temperatures 
                WHERE sensor_id = ? AND timestamp > ?
            """, (sensor_id, since))
            result = dict(cursor.fetchone())
            conn.close()
            return result

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
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results
    
    @staticmethod
    def cleanup_old_logs(days=7):
        """古いログを削除"""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            # JST時刻で計算
            since = (get_jst_now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("DELETE FROM system_logs WHERE timestamp < ?", (since,))
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted
