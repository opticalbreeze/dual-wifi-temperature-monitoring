"""
temperature_server/services/background_tasks.py
バックグラウンドタスク（ヘルスチェック、メモリ監視）
"""

import threading
import time
import psutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """バックグラウンドタスク管理"""
    
    def __init__(self):
        self.running = False
        self.threads = []
        self.last_cleanup = datetime.now()
    
    def start(self):
        """すべてのバックグラウンドタスクを開始"""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting background tasks...")
        
        # メモリ監視タスク
        self.start_memory_monitor()
        
        # WiFi ヘルスチェックタスク
        self.start_wifi_health_check()
        
        # ログクリーンアップタスク
        self.start_log_cleanup()
        
        logger.info(f"✓ Background tasks started ({len(self.threads)} threads)")
    
    def stop(self):
        """すべてのバックグラウンドタスクを停止"""
        self.running = False
        logger.info("Stopping background tasks...")
        
        for thread in self.threads:
            thread.join(timeout=5)
        
        logger.info("✓ Background tasks stopped")
    
    def start_memory_monitor(self):
        """メモリ使用率を監視"""
        def monitor():
            while self.running:
                try:
                    mem = psutil.virtual_memory()
                    
                    if mem.percent >= Config.MEMORY_THRESHOLD:
                        logger.warning(
                            f"⚠️  Memory usage high: {mem.percent}% "
                            f"(threshold: {Config.MEMORY_THRESHOLD}%)"
                        )
                        
                        # キャッシュをクリア
                        try:
                            import subprocess
                            subprocess.run(['sync'], timeout=5)
                            logger.info("✓ Cache cleared")
                        except Exception as e:
                            logger.warning(f"Failed to clear cache: {e}")
                    
                    time.sleep(Config.MEMORY_CHECK_INTERVAL)
                
                except Exception as e:
                    logger.error(f"Memory monitor error: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=monitor, daemon=True, name="MemoryMonitor")
        thread.start()
        self.threads.append(thread)
    
    def start_wifi_health_check(self):
        """WiFi のヘルスチェック"""
        def health_check():
            from services.wifi_manager import WiFiManager
            wifi_manager = WiFiManager()
            
            while self.running:
                try:
                    health = wifi_manager.health_check()
                    
                    if health.get('overall') != 'healthy':
                        logger.warning(f"WiFi health: {health.get('overall')}")
                    
                    time.sleep(Config.WIFI_CHECK_INTERVAL)
                
                except Exception as e:
                    logger.error(f"WiFi health check error: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=health_check, daemon=True, name="WiFiHealthCheck")
        thread.start()
        self.threads.append(thread)
    
    def start_log_cleanup(self):
        """古いログファイルをクリーンアップ"""
        def cleanup():
            from database.queries import SystemLogQueries
            
            while self.running:
                try:
                    # 古いログを削除
                    deleted = SystemLogQueries.cleanup_old_logs(
                        days=Config.LOG_RETENTION_DAYS
                    )
                    if deleted > 0:
                        logger.info(f"Cleaned up {deleted} old log entries")
                    
                    # 24時間ごとに実行
                    time.sleep(86400)
                
                except Exception as e:
                    logger.error(f"Log cleanup error: {e}")
                    time.sleep(3600)
        
        thread = threading.Thread(target=cleanup, daemon=True, name="LogCleanup")
        thread.start()
        self.threads.append(thread)

# グローバルインスタンス
background_tasks = BackgroundTaskManager()
