"""
バリデーション関数
"""

from typing import Tuple, Optional, Dict, Any
from utils.exceptions import ValidationException, SensorException


def validate_sensor_id(sensor_id: Any) -> Tuple[bool, Optional[str]]:
    """
    センサーIDをバリデーション
    
    Returns:
        (is_valid, error_message)
    """
    if not sensor_id:
        return False, "センサーIDが指定されていません"
    
    if not isinstance(sensor_id, str):
        return False, "センサーIDは文字列である必要があります"
    
    if len(sensor_id) > 100:
        return False, "センサーIDが長すぎます（最大100文字）"
    
    if len(sensor_id.strip()) == 0:
        return False, "センサーIDが空です"
    
    return True, None


def validate_temperature(temperature: Any) -> Tuple[bool, Optional[str]]:
    """
    温度値をバリデーション
    
    Returns:
        (is_valid, error_message)
    """
    if temperature is None:
        return False, "温度値が指定されていません"
    
    try:
        temp_float = float(temperature)
    except (ValueError, TypeError):
        return False, "温度値は数値である必要があります"
    
    # 合理的な範囲チェック（-50°C ～ 100°C）
    if temp_float < -50 or temp_float > 100:
        return False, f"温度値が範囲外です（-50°C ～ 100°C）: {temp_float}°C"
    
    return True, None


def validate_humidity(humidity: Any) -> Tuple[bool, Optional[str]]:
    """
    湿度値をバリデーション（オプション）
    
    Returns:
        (is_valid, error_message)
    """
    if humidity is None:
        return True, None  # オプショナルなのでNoneはOK
    
    try:
        hum_float = float(humidity)
    except (ValueError, TypeError):
        return False, "湿度値は数値である必要があります"
    
    if hum_float < 0 or hum_float > 100:
        return False, f"湿度値が範囲外です（0% ～ 100%）: {hum_float}%"
    
    return True, None


def validate_temperature_request(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    温度データリクエスト全体をバリデーション
    
    Returns:
        (is_valid, error_message, validated_data)
    """
    if not data:
        return False, "リクエストデータが空です", {}
    
    # sensor_idの取得とバリデーション
    sensor_id = data.get('device_id') or data.get('sensor_id')
    is_valid, error_msg = validate_sensor_id(sensor_id)
    if not is_valid:
        return False, error_msg, {}
    
    # temperatureの取得とバリデーション
    temperature = data.get('temperature') or data.get('temp')
    is_valid, error_msg = validate_temperature(temperature)
    if not is_valid:
        return False, error_msg, {}
    
    # humidityのバリデーション（オプション）
    humidity = data.get('humidity')
    if humidity is not None:
        is_valid, error_msg = validate_humidity(humidity)
        if not is_valid:
            return False, error_msg, {}
    
    # バリデーション済みデータを構築
    validated_data = {
        'sensor_id': sensor_id,
        'temperature': float(temperature),
        'sensor_name': data.get('name') or data.get('sensor_name', 'Unknown'),
        'humidity': float(humidity) if humidity is not None else None,
        'rssi': data.get('rssi'),
        'battery_mode': bool(data.get('battery_mode', False)),
        'location': data.get('location', 'Not set')
    }
    
    return True, None, validated_data


def validate_hours(hours: Any) -> Tuple[bool, Optional[str], Optional[float]]:
    """
    時間範囲をバリデーション
    
    Returns:
        (is_valid, error_message, validated_hours)
    """
    if hours is None:
        return True, None, 24.0  # デフォルト値
    
    try:
        hours_float = float(hours)
    except (ValueError, TypeError):
        return False, "時間範囲は数値である必要があります", None
    
    if hours_float <= 0:
        return False, "時間範囲は0より大きい必要があります", None
    
    if hours_float > 8760:  # 1年 = 365日 * 24時間
        return False, "時間範囲が長すぎます（最大1年）", None
    
    return True, None, hours_float


def validate_sensor_ids(sensor_ids: Any) -> Tuple[bool, Optional[str], Optional[list]]:
    """
    センサーIDリストをバリデーション
    
    Returns:
        (is_valid, error_message, validated_ids)
    """
    if not sensor_ids:
        return False, "センサーIDリストが指定されていません", None
    
    if not isinstance(sensor_ids, list):
        return False, "センサーIDリストは配列である必要があります", None
    
    if len(sensor_ids) == 0:
        return False, "センサーIDリストが空です", None
    
    if len(sensor_ids) > 100:
        return False, "センサーIDリストが長すぎます（最大100件）", None
    
    # 各IDをバリデーション
    validated_ids = []
    for idx, sensor_id in enumerate(sensor_ids):
        is_valid, error_msg = validate_sensor_id(sensor_id)
        if not is_valid:
            return False, f"センサーID[{idx}]: {error_msg}", None
        validated_ids.append(sensor_id)
    
    return True, None, validated_ids

