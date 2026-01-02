"""
temperature_server/app/__init__.py
Flask アプリケーション初期化
"""

from flask import Flask, request
from flask_cors import CORS
from flask_compress import Compress
from pathlib import Path
from config import Config
from logger import setup_logger

logger = setup_logger(__name__)

def create_app():
    """Flask アプリケーションを作成"""
    # プロジェクトルートを取得（app/__init__.pyの親の親）
    project_root = Path(__file__).parent.parent
    app = Flask(__name__, template_folder=str(project_root / 'templates'), static_folder=str(project_root / 'app' / 'static'))
    
    # Flask設定
    app.config['ENV'] = Config.FLASK_ENV
    app.config['DEBUG'] = Config.FLASK_DEBUG
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    
    # gzip圧縮を有効化（通信量削減）
    Compress(app)
    logger.info("Response compression (gzip) enabled")
    
    # ===== リクエストロギングミドルウェア（全リクエストを記録） =====
    @app.before_request
    def log_request():
        """すべてのリクエストをログに記録（ESP32からのPOST検証用）"""
        logger.debug(f"[REQUEST] {request.method} {request.path} from {request.remote_addr}")
    
    @app.after_request
    def log_response(response):
        """すべてのレスポンスをログに記録"""
        logger.debug(f"[RESPONSE] {request.method} {request.path} -> {response.status_code}")
        return response
    
    # CORS設定（ホワイトリスト方式）
    cors_config = {
        "origins": Config.ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "max_age": 3600
    }
    
    CORS(app, resources={
        r"/api/*": cors_config,
        r"/wifi/*": cors_config,
        r"/*": cors_config
    })
    
    logger.info(f"CORS configured for origins: {Config.ALLOWED_ORIGINS}")
    
    # ブループリント登録
    try:
        from app.routes.wifi import wifi_bp
        app.register_blueprint(wifi_bp)
        logger.info("Registered wifi blueprint")
    except ImportError as e:
        logger.warning(f"Failed to register wifi blueprint: {e}")
    
    # APIブループリント（存在する場合）
    try:
        from app.routes.api import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')
        logger.info("Registered api blueprint")
    except ImportError:
        logger.warning("api blueprint not found, skipping")
    
    # ダッシュボードブループリント（存在する場合）
    try:
        from app.routes.dashboard import dashboard_bp
        app.register_blueprint(dashboard_bp)
        logger.info("Registered dashboard blueprint")
    except ImportError:
        logger.warning("dashboard blueprint not found, skipping")
    
    return app

