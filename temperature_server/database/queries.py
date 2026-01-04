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


def _downsample_temperature_data(data_points, max_points):
    """
    温度データを間引き（最大値・最小値・急激な変化を保持）
    
    Args:
        data_points: 温度データのリスト（dict形式、temperatureキーを含む）
        max_points: 最大データポイント数
    
    Returns:
        間引き後のデータポイントリスト
    """
    if len(data_points) <= max_points:
        return data_points
    
    downsampled = []
    
    # 1. 最初と最後のポイントは必ず含める
    downsampled.append(data_points[0])
    
    # 2. 最大値・最小値を検出して保持
    max_temp = data_points[0].get('temperature', 0)
    min_temp = data_points[0].get('temperature', 0)
    max_index = 0
    min_index = 0
    
    for i in range(1, len(data_points) - 1):
        temp = data_points[i].get('temperature', 0)
        if temp > max_temp:
            max_temp = temp
            max_index = i
        if temp < min_temp:
            min_temp = temp
            min_index = i
    
    # 重複チェック用のセット（O(1)参照で高速化）
    added_indices = {0}  # 最初のポイントのインデックス
    
    # 最大値・最小値のポイントを追加（重複チェック）
    if max_index > 0 and max_index < len(data_points) - 1:
        if max_index not in added_indices:
            downsampled.append(data_points[max_index])
            added_indices.add(max_index)
    
    if min_index > 0 and min_index < len(data_points) - 1 and min_index != max_index:
        if min_index not in added_indices:
            downsampled.append(data_points[min_index])
            added_indices.add(min_index)
    
    # 3. 急激な変化（変化率が大きい箇所）を検出して保持
    change_threshold = 0.5  # 0.5°C以上の変化を検出
    important_indices = set()
    
    for i in range(1, len(data_points) - 1):
        prev_temp = data_points[i - 1].get('temperature', 0)
        curr_temp = data_points[i].get('temperature', 0)
        next_temp = data_points[i + 1].get('temperature', 0)
        
        # 前後のポイントとの変化率を計算
        change1 = abs(curr_temp - prev_temp)
        change2 = abs(next_temp - curr_temp)
        
        # 急激な変化がある場合は保持
        if change1 > change_threshold or change2 > change_threshold:
            important_indices.add(i)
    
    # 重要ポイントを追加（最大値・最小値と重複しないように）
    for index in important_indices:
        if index not in added_indices:
            downsampled.append(data_points[index])
            added_indices.add(index)
    
    # 4. 残りのポイントを均等に間引き
    remaining_slots = max_points - len(downsampled) - 1  # -1は最後のポイント用
    if remaining_slots > 0:
        adjusted_step = max(1, (len(data_points) - 1) // remaining_slots)
        for i in range(adjusted_step, len(data_points) - 1, adjusted_step):
            # 既に追加されているポイントはスキップ
            if i not in added_indices:
                downsampled.append(data_points[i])
                added_indices.add(i)
    
    # 5. 最後のポイントを追加
    if len(data_points) > 1:
        last_index = len(data_points) - 1
        if last_index not in added_indices:
            downsampled.append(data_points[last_index])
            added_indices.add(last_index)
    
    # 6. タイムスタンプでソート（順序を保証）
    downsampled.sort(key=lambda x: x.get('timestamp', ''))
    
    return downsampled


class TemperatureQueries:
    
    @staticmethod
    def insert_reading(sensor_id, temperature, sensor_name=None, humidity=None, rssi=None, battery_mode=False, connection_type=None):
        """温度データを挿入（JSTタイムゾーン）"""
        with db_lock:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                # JSTタイムゾーンで現在時刻を取得
                now = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
                
                # connection_type を自動判定（指定なしの場合）
                if connection_type is None:
                    # RSSIがある=WiFi AP直接接続、無い=ESP-NOW
                    connection_type = 'wifi_ap' if rssi is not None else 'esp_now'
                
                cursor.execute("""
                    INSERT INTO temperatures 
                    (sensor_id, sensor_name, temperature, humidity, rssi, battery_mode, connection_type, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (sensor_id, sensor_name, temperature, humidity, rssi, int(battery_mode), connection_type, now))
                conn.commit()
            finally:
                conn.close()
    
    @staticmethod
    def get_latest_reading(sensor_id):
        """センサーの最新データを取得"""
        with db_lock:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM temperatures 
                    WHERE sensor_id = ? 
                    ORDER BY timestamp DESC LIMIT 1
                """, (sensor_id,))
                result = cursor.fetchone()
                if result:
                    return dict(result)
                return None
            finally:
                conn.close()
    
    @staticmethod
    def get_all_latest():
        """全センサーの最新データを取得"""
        import logging
        db_logger = logging.getLogger('database.queries')
        with db_lock:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                
                # 全センサーの最新データを1つのクエリで取得（デッドロック回避）
                # MAX(timestamp) で時系列最新を取得（MAX(id)でなく）
                cursor.execute("""
                    SELECT t1.* FROM temperatures t1
                    WHERE t1.timestamp = (
                        SELECT MAX(timestamp) FROM temperatures t2 
                        WHERE t2.sensor_id = t1.sensor_id
                    )
                    ORDER BY t1.sensor_id
                """)
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
                
                db_logger.info(f"get_all_latest: Found {len(results)} sensors")
                for data in results:
                    db_logger.debug(f"get_all_latest: Sensor: {data.get('sensor_id')}, Temp: {data.get('temperature')}, Time: {data.get('timestamp')}")
                
                return results
            finally:
                conn.close()
    
    @staticmethod
    def get_range(sensor_id, hours=24):
        """指定時間範囲のデータを取得（JSTタイムゾーン）"""
        with db_lock:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                # JSTタイムゾーンで指定時間前の時刻を計算
                since = (datetime.now(JST) - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("""
                    SELECT * FROM temperatures 
                    WHERE sensor_id = ? AND timestamp >= ?
                    ORDER BY timestamp ASC
                """, (sensor_id, since))
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
                return results
            finally:
                conn.close()
    
    @staticmethod
    def get_statistics(sensor_id, hours=24):
        """温度統計を計算（JSTタイムゾーン）"""
        with db_lock:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                # JSTタイムゾーンで指定時間前の時刻を計算
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
                if result:
                    return dict(result)
                return {}
            finally:
                conn.close()
    
    @staticmethod
    def get_range_batch(sensor_ids, hours=24, max_points_per_sensor=500):
        """複数センサーの指定時間範囲のデータを一括取得（高速化・間引き対応）"""
        # 入力検証
        if not sensor_ids:
            return {}
        
        if not isinstance(sensor_ids, (list, tuple)):
            raise ValueError("sensor_ids must be a list or tuple")
        
        # 空のリストを除外し、文字列型を検証
        valid_sensor_ids = []
        for sensor_id in sensor_ids:
            if isinstance(sensor_id, str) and sensor_id.strip() and len(sensor_id) <= 100:
                valid_sensor_ids.append(sensor_id.strip())
        
        if not valid_sensor_ids:
            return {}
        
        # hours の検証
        if not isinstance(hours, (int, float)) or hours <= 0 or hours > 8760:
            raise ValueError("hours must be between 0 and 8760")
        
        # max_points_per_sensor の検証
        if not isinstance(max_points_per_sensor, int) or max_points_per_sensor <= 0 or max_points_per_sensor > 10000:
            raise ValueError("max_points_per_sensor must be between 1 and 10000")
        
        with db_lock:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                # JSTタイムゾーンで指定時間前の時刻を計算
                since = (datetime.now(JST) - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
                
                # プレースホルダーを生成（検証済みのIDのみ使用）
                placeholders = ','.join(['?' for _ in valid_sensor_ids])
                
                # 全データを取得（間引きはPython側で実施）
                query = f"""
                    SELECT * FROM temperatures 
                    WHERE sensor_id IN ({placeholders}) AND timestamp >= ?
                    ORDER BY sensor_id, timestamp ASC
                """
                cursor.execute(query, tuple(valid_sensor_ids) + (since,))
                
                rows = cursor.fetchall()
                
                # センサーIDごとにグループ化
                results = {}
                for row in rows:
                    sensor_id = row['sensor_id']
                    if sensor_id not in results:
                        results[sensor_id] = []
                    results[sensor_id].append(dict(row))
                
                # さらにPython側で間引き（最大値・最小値・急激な変化を保持）
                for sensor_id in results:
                    if len(results[sensor_id]) > max_points_per_sensor:
                        original = results[sensor_id]
                        downsampled = _downsample_temperature_data(original, max_points_per_sensor)
                        results[sensor_id] = downsampled
                
                return results
            finally:
                conn.close()

class SystemLogQueries:
    
    @staticmethod
    def insert_log(level, module, message):
        """システムログを挿入"""
        with db_lock:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO system_logs (level, module, message)
                    VALUES (?, ?, ?)
                """, (level, module, message))
                conn.commit()
            finally:
                conn.close()
    
    @staticmethod
    def get_recent_logs(limit=100):
        """最近のログを取得"""
        with db_lock:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM system_logs 
                    ORDER BY timestamp DESC LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
                return results
            finally:
                conn.close()
    
    @staticmethod
    def cleanup_old_logs(days=7):
        """古いログを削除（JSTタイムゾーン）"""
        with db_lock:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                since = (datetime.now(JST) - timedelta(days=days)).isoformat()
                cursor.execute("DELETE FROM system_logs WHERE timestamp < ?", (since,))
                deleted = cursor.rowcount
                conn.commit()
                return deleted
            finally:
                conn.close()


    @staticmethod
    def delete_old_records(days_old=30):
        """指定日数以前のデータを削除（JSTタイムゾーン）"""
        with db_lock:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                since = (datetime.now(JST) - timedelta(days=days_old)).strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("DELETE FROM temperatures WHERE timestamp < ?", (since,))
                deleted = cursor.rowcount
                conn.commit()
                return deleted
            finally:
                conn.close()

    @staticmethod
    def delete_test_sensors():
        """テストセンサーのデータを削除"""
        with db_lock:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM temperatures WHERE sensor_id LIKE ?", ('%TEST%',))
                deleted = cursor.rowcount
                conn.commit()
                return deleted
            finally:
                conn.close()

