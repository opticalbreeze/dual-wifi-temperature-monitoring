"""
APIバリデーション関数のユニットテスト
"""

import unittest
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.routes.api import (
    validate_temperature_request,
    validate_hours_param,
    TEMPERATURE_MIN,
    TEMPERATURE_MAX,
    HOURS_MIN,
    HOURS_MAX
)
from app.exceptions import (
    TemperatureOutOfRangeError,
    InvalidSensorIdError,
    InvalidTemperatureError,
    InvalidJSONError,
    InvalidHoursParameterError
)


class TestValidateTemperatureRequest(unittest.TestCase):
    """温度データリクエストのバリデーションテスト"""
    
    def test_valid_request_with_device_id(self):
        """正常なリクエスト（device_id使用）"""
        data = {
            "device_id": "ESP32_01",
            "temperature": 25.5,
            "name": "テストセンサー"
        }
        is_valid, result = validate_temperature_request(data)
        self.assertTrue(is_valid)
        self.assertEqual(result['sensor_id'], "ESP32_01")
        self.assertEqual(result['temperature'], 25.5)
        self.assertEqual(result['sensor_name'], "テストセンサー")
    
    def test_valid_request_with_sensor_id(self):
        """正常なリクエスト（sensor_id使用）"""
        data = {
            "sensor_id": "ESP32_02",
            "temperature": 20.0,
            "sensor_name": "センサー02"
        }
        is_valid, result = validate_temperature_request(data)
        self.assertTrue(is_valid)
        self.assertEqual(result['sensor_id'], "ESP32_02")
        self.assertEqual(result['temperature'], 20.0)
    
    def test_valid_request_with_humidity(self):
        """正常なリクエスト（湿度含む）"""
        data = {
            "device_id": "ESP32_01",
            "temperature": 25.5,
            "humidity": 55.2
        }
        is_valid, result = validate_temperature_request(data)
        self.assertTrue(is_valid)
        self.assertEqual(result['humidity'], 55.2)
    
    def test_invalid_not_dict(self):
        """無効なリクエスト（辞書でない）"""
        data = "not a dict"
        is_valid, result = validate_temperature_request(data)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, InvalidJSONError)
    
    def test_missing_sensor_id(self):
        """無効なリクエスト（センサーIDなし）"""
        data = {
            "temperature": 25.5
        }
        is_valid, result = validate_temperature_request(data)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, InvalidSensorIdError)
    
    def test_missing_temperature(self):
        """無効なリクエスト（温度なし）"""
        data = {
            "device_id": "ESP32_01"
        }
        is_valid, result = validate_temperature_request(data)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, InvalidTemperatureError)
    
    def test_invalid_temperature_string(self):
        """無効なリクエスト（温度が文字列）"""
        data = {
            "device_id": "ESP32_01",
            "temperature": "not a number"
        }
        is_valid, result = validate_temperature_request(data)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, InvalidTemperatureError)
    
    def test_temperature_too_high(self):
        """無効なリクエスト（温度が高すぎる）"""
        data = {
            "device_id": "ESP32_01",
            "temperature": 100.0
        }
        is_valid, result = validate_temperature_request(data)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, TemperatureOutOfRangeError)
        self.assertEqual(result.temperature, 100.0)
        self.assertEqual(result.max_temp, TEMPERATURE_MAX)
    
    def test_temperature_too_low(self):
        """無効なリクエスト（温度が低すぎる）"""
        data = {
            "device_id": "ESP32_01",
            "temperature": -100.0
        }
        is_valid, result = validate_temperature_request(data)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, TemperatureOutOfRangeError)
        self.assertEqual(result.temperature, -100.0)
        self.assertEqual(result.min_temp, TEMPERATURE_MIN)
    
    def test_temperature_at_boundary_min(self):
        """境界値テスト（最小値）"""
        data = {
            "device_id": "ESP32_01",
            "temperature": TEMPERATURE_MIN
        }
        is_valid, result = validate_temperature_request(data)
        self.assertTrue(is_valid)
        self.assertEqual(result['temperature'], TEMPERATURE_MIN)
    
    def test_temperature_at_boundary_max(self):
        """境界値テスト（最大値）"""
        data = {
            "device_id": "ESP32_01",
            "temperature": TEMPERATURE_MAX
        }
        is_valid, result = validate_temperature_request(data)
        self.assertTrue(is_valid)
        self.assertEqual(result['temperature'], TEMPERATURE_MAX)
    
    def test_temperature_none(self):
        """無効なリクエスト（温度がNone）"""
        data = {
            "device_id": "ESP32_01",
            "temperature": None
        }
        is_valid, result = validate_temperature_request(data)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, InvalidTemperatureError)
    
    def test_sensor_id_empty_string(self):
        """無効なリクエスト（センサーIDが空文字列）"""
        data = {
            "device_id": "",
            "temperature": 25.5
        }
        is_valid, result = validate_temperature_request(data)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, InvalidSensorIdError)
    
    def test_sensor_id_not_string(self):
        """無効なリクエスト（センサーIDが文字列でない）"""
        data = {
            "device_id": 12345,
            "temperature": 25.5
        }
        is_valid, result = validate_temperature_request(data)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, InvalidSensorIdError)


class TestValidateHoursParam(unittest.TestCase):
    """hoursパラメータのバリデーションテスト"""
    
    def test_valid_hours_int(self):
        """正常なhours（整数）"""
        hours = 24
        is_valid, result = validate_hours_param(hours)
        self.assertTrue(is_valid)
        self.assertEqual(result, 24)
    
    def test_valid_hours_float(self):
        """正常なhours（浮動小数点数）"""
        hours = 0.5
        is_valid, result = validate_hours_param(hours)
        self.assertTrue(is_valid)
        self.assertEqual(result, 0.5)
    
    def test_valid_hours_at_min(self):
        """境界値テスト（最小値）"""
        hours = HOURS_MIN
        is_valid, result = validate_hours_param(hours)
        self.assertTrue(is_valid)
        self.assertEqual(result, HOURS_MIN)
    
    def test_valid_hours_at_max(self):
        """境界値テスト（最大値）"""
        hours = HOURS_MAX
        is_valid, result = validate_hours_param(hours)
        self.assertTrue(is_valid)
        self.assertEqual(result, HOURS_MAX)
    
    def test_invalid_hours_too_small(self):
        """無効なhours（小さすぎる）"""
        hours = 0.1
        is_valid, result = validate_hours_param(hours)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, InvalidHoursParameterError)
        self.assertEqual(result.hours, 0.1)
    
    def test_invalid_hours_too_large(self):
        """無効なhours（大きすぎる）"""
        hours = 1000
        is_valid, result = validate_hours_param(hours)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, InvalidHoursParameterError)
        self.assertEqual(result.hours, 1000)
    
    def test_invalid_hours_negative(self):
        """無効なhours（負の値）"""
        hours = -1
        is_valid, result = validate_hours_param(hours)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, InvalidHoursParameterError)
    
    def test_invalid_hours_string(self):
        """無効なhours（文字列）"""
        hours = "24"
        is_valid, result = validate_hours_param(hours)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, InvalidHoursParameterError)
    
    def test_invalid_hours_none(self):
        """無効なhours（None）"""
        hours = None
        is_valid, result = validate_hours_param(hours)
        self.assertFalse(is_valid)
        self.assertIsInstance(result, InvalidHoursParameterError)


if __name__ == '__main__':
    unittest.main()

