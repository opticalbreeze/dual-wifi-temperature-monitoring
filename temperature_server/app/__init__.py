from flask import Flask
from flask_cors import CORS
from config import Config
from logger import setup_logger
from pathlib import Path

logger = setup_logger(__name__)

def create_app():
    template_dir = Path(__file__).parent.parent / 'templates'
    static_dir = Path(__file__).parent / 'static'
    
    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir)
    )
    
    app.config['ENV'] = Config.FLASK_ENV
    app.config['DEBUG'] = Config.FLASK_DEBUG
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    
    CORS(app)
    
    logger.info(f"Flask app created (ENV: {Config.FLASK_ENV})")
    
    from app.routes.dashboard import dashboard_bp
    from app.routes.api import api_bp
    from app.routes.wifi import wifi_bp
    
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(wifi_bp)
    
    from services.background_tasks import background_tasks
    background_tasks.start()
    
    return app
