"""
統一されたエラーハンドリングシステム
"""

from typing import Optional, Dict, Any
import traceback


class BaseApplicationException(Exception):
    """アプリケーション基本例外クラス"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "status": "error",
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ValidationException(BaseApplicationException):
    """バリデーションエラー"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if field:
            details['field'] = field
        super().__init__(
            message=message,
            error_code='VALIDATION_ERROR',
            details=details,
            status_code=400,
            **kwargs
        )


class DatabaseException(BaseApplicationException):
    """データベースエラー"""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if operation:
            details['operation'] = operation
        super().__init__(
            message=message,
            error_code='DATABASE_ERROR',
            details=details,
            status_code=500,
            **kwargs
        )


class SensorException(BaseApplicationException):
    """センサー関連エラー"""
    
    def __init__(self, message: str, sensor_id: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if sensor_id:
            details['sensor_id'] = sensor_id
        super().__init__(
            message=message,
            error_code='SENSOR_ERROR',
            details=details,
            status_code=400,
            **kwargs
        )


class WiFiException(BaseApplicationException):
    """WiFi関連エラー"""
    
    def __init__(self, message: str, interface: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if interface:
            details['interface'] = interface
        super().__init__(
            message=message,
            error_code='WIFI_ERROR',
            details=details,
            status_code=500,
            **kwargs
        )


def format_exception(e: Exception) -> Dict[str, Any]:
    """例外を構造化された辞書に変換"""
    return {
        "type": type(e).__name__,
        "message": str(e),
        "traceback": traceback.format_exc() if isinstance(e, BaseApplicationException) else None
    }

