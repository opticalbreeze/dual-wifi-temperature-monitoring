"""
統一されたエラーハンドリングデコレータ
"""

from functools import wraps
from flask import jsonify, g
from typing import Callable, Any
from logger import setup_logger
from utils.exceptions import (
    BaseApplicationException,
    ValidationException,
    DatabaseException,
    SensorException,
    format_exception
)
from utils.request_tracing import get_request_id, log_with_request_id

logger = setup_logger(__name__)


def handle_errors(f: Callable) -> Callable:
    """
    統一されたエラーハンドリングデコレータ
    
    使用例:
        @api_bp.route('/api/temperature', methods=['POST'])
        @handle_errors
        def receive_temperature():
            # 処理...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        
        except ValidationException as e:
            # バリデーションエラー（400）
            log_with_request_id(
                f"Validation error: {e.message} (code: {e.error_code})",
                level='warning'
            )
            response = e.to_dict()
            response['request_id'] = get_request_id()
            return jsonify(response), e.status_code
        
        except SensorException as e:
            # センサー関連エラー（400）
            log_with_request_id(
                f"Sensor error: {e.message} (code: {e.error_code})",
                level='warning'
            )
            response = e.to_dict()
            response['request_id'] = get_request_id()
            return jsonify(response), e.status_code
        
        except DatabaseException as e:
            # データベースエラー（500）
            log_with_request_id(
                f"Database error: {e.message} (code: {e.error_code})",
                level='error'
            )
            response = e.to_dict()
            response['request_id'] = get_request_id()
            # 本番環境では詳細情報を隠す
            if hasattr(g, 'app') and g.app.config.get('FLASK_ENV') == 'production':
                response['details'] = {}
            return jsonify(response), e.status_code
        
        except BaseApplicationException as e:
            # その他のアプリケーションエラー
            log_with_request_id(
                f"Application error: {e.message} (code: {e.error_code})",
                level='error'
            )
            response = e.to_dict()
            response['request_id'] = get_request_id()
            return jsonify(response), e.status_code
        
        except Exception as e:
            # 予期しないエラー
            error_info = format_exception(e)
            log_with_request_id(
                f"Unexpected error: {error_info['type']}: {error_info['message']}",
                level='error'
            )
            
            response = {
                "status": "error",
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "予期しないエラーが発生しました",
                "request_id": get_request_id()
            }
            
            # 開発環境では詳細情報を含める
            if hasattr(g, 'app') and g.app.config.get('FLASK_DEBUG'):
                response['details'] = error_info
            
            logger.error(
                f"[{get_request_id()}] Unexpected error: {error_info['type']}",
                exc_info=True
            )
            
            return jsonify(response), 500
    
    return decorated_function

