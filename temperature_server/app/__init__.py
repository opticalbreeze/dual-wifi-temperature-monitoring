"""
temperature_server/app/__init__.py
Flask アプリケーション初期化
"""

from flask import Flask, request
from flask_cors import CORS
from pathlib import Path
from config import Config
from logger import setup_logger

# flask_compressはオプション（インストールされていなくても動作する）
try:
    from flask_compress import Compress
    compress_available = True
except ImportError:
    compress_available = False

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
    
    # gzip圧縮を有効化（通信量削減、オプション）
    if compress_available:
        Compress(app)
        logger.info("Response compression (gzip) enabled")
    else:
        logger.info("Response compression disabled (flask-compress not installed)")
    
    # ===== リクエストロギングミドルウェア（全リクエストを記録） =====
    @app.before_request
    def log_request():
        """すべてのリクエストをログに記録（ESP32からのPOST検証用）"""
        logger.info(f"[REQUEST] {request.method} {request.path} from {request.remote_addr}")
        logger.info(f"[REQUEST] Query string: {request.query_string.decode()}")
        logger.info(f"[REQUEST] Headers: {dict(request.headers)}")
        
        # DELETEリクエストの詳細ログ
        if request.method == 'DELETE' and '/api/sensors/' in request.path:
            logger.info(f"[DELETE DEBUG] Path: {request.path}")
            logger.info(f"[DELETE DEBUG] Full URL: {request.url}")
            logger.info(f"[DELETE DEBUG] View function: {request.endpoint if hasattr(request, 'endpoint') else 'unknown'}")
    
    @app.after_request
    def log_response(response):
        """すべてのレスポンスをログに記録"""
        logger.info(f"[RESPONSE] {request.method} {request.path} -> {response.status_code}")
        
        # DELETEリクエストの詳細ログ
        if request.method == 'DELETE' and '/api/sensors/' in request.path:
            logger.info(f"[DELETE DEBUG] Response status: {response.status_code}")
            logger.info(f"[DELETE DEBUG] Response Content-Type: {response.headers.get('Content-Type')}")
            logger.info(f"[DELETE DEBUG] Response size: {response.content_length if hasattr(response, 'content_length') else 'unknown'}")
        
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
        logger.info("=" * 80)
        logger.info("✅ Registered api blueprint with prefix '/api'")
        
        # 登録されたルートを確認
        logger.info("Registered API routes:")
        for rule in app.url_map.iter_rules():
            if rule.rule.startswith('/api'):
                logger.info(f"  {rule.methods} {rule.rule}")
        logger.info("=" * 80)
    except ImportError as e:
        logger.error("=" * 80)
        logger.error(f"❌ Failed to register api blueprint: {e}")
        logger.error("=" * 80)
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ Error registering api blueprint: {e}", exc_info=True)
        logger.error("=" * 80)
    
    # ダッシュボードブループリント（存在する場合）
    try:
        from app.routes.dashboard import dashboard_bp
        app.register_blueprint(dashboard_bp)
        logger.info("Registered dashboard blueprint")
    except ImportError:
        logger.warning("dashboard blueprint not found, skipping")
    
    # 404エラーハンドラー（APIエンドポイント用）
    @app.errorhandler(404)
    def not_found(error):
        """404エラーをJSONで返す（APIエンドポイント用）"""
        if request.path.startswith('/api/'):
            from flask import jsonify
            return jsonify({
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": f"API endpoint not found: {request.path}",
                "path": request.path
            }), 404
        # API以外は通常の404処理
        return error
    
    # 500エラーハンドラー（APIエンドポイント用）
    @app.errorhandler(500)
    def internal_error(error):
        """500エラーをJSONで返す（APIエンドポイント用）"""
        if request.path.startswith('/api/'):
            from flask import jsonify
            return jsonify({
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "path": request.path
            }), 500
        # API以外は通常の500処理
        return error
    
    return app

