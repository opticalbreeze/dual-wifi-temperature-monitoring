"""
カスタム例外クラス定義
APIエラーハンドリング用
"""


class TemperatureOutOfRangeError(ValueError):
    """温度が有効範囲外の場合"""
    def __init__(self, temperature, min_temp=-50, max_temp=70):
        self.temperature = temperature
        self.min_temp = min_temp
        self.max_temp = max_temp
        message = f"Temperature {temperature}°C is out of valid range ({min_temp}~{max_temp}°C)"
        super().__init__(message)


class InvalidSensorIdError(ValueError):
    """無効なセンサーID"""
    def __init__(self, sensor_id=None):
        self.sensor_id = sensor_id
        message = "Missing or invalid sensor_id (device_id or sensor_id)"
        if sensor_id:
            message = f"Invalid sensor_id: {sensor_id}"
        super().__init__(message)


class InvalidTemperatureError(ValueError):
    """無効な温度値（数値でない、またはNone）"""
    def __init__(self, temperature=None):
        self.temperature = temperature
        message = "Temperature must be numeric"
        if temperature is not None:
            message = f"Invalid temperature value: {temperature}"
        super().__init__(message)


class InvalidHoursParameterError(ValueError):
    """無効なhoursパラメータ"""
    def __init__(self, hours, min_hours=0.5, max_hours=720):
        self.hours = hours
        self.min_hours = min_hours
        self.max_hours = max_hours
        message = f"hours parameter {hours} is out of valid range ({min_hours}~{max_hours})"
        super().__init__(message)


class InvalidJSONError(ValueError):
    """無効なJSON形式"""
    def __init__(self, message="Invalid JSON format"):
        super().__init__(message)


class DatabaseError(Exception):
    """データベース操作エラー"""
    def __init__(self, operation, message=None):
        self.operation = operation
        self.message = message or f"Database error during {operation}"
        super().__init__(self.message)

