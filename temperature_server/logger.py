import logging
import logging.handlers
from pathlib import Path
from config import Config

def setup_logger(name):
    """ロガーセットアップ"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # ファイルハンドラ
    log_file = Config.LOGS_DIR / f'{name}.log'
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    handler = logging.handlers.RotatingFileHandler(
        str(log_file),
        maxBytes=Config.LOG_MAX_BYTES,
        backupCount=Config.LOG_BACKUP_COUNT
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # コンソールハンドラ
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    return logger
