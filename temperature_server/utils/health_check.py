"""
ヘルスチェック機能
システムの状態を監視
"""

from typing import Dict, Any, List
from datetime import datetime
from logger import setup_logger
from database.queries import TemperatureQueries

logger = setup_logger(__name__)


class HealthChecker:
    """システムヘルスチェック"""
    
    @staticmethod
    def check_database() -> Dict[str, Any]:
        """データベース接続チェック"""
        try:
            sensors = TemperatureQueries.get_all_latest()
            return {
                "status": "healthy",
                "message": "データベース接続正常",
                "sensor_count": len(sensors)
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"データベース接続エラー: {str(e)}",
                "error": str(e)
            }
    
    @staticmethod
    def check_disk_space() -> Dict[str, Any]:
        """ディスク容量チェック"""
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            free_percent = (free / total) * 100
            
            status = "healthy" if free_percent > 10 else "warning" if free_percent > 5 else "unhealthy"
            
            return {
                "status": status,
                "message": f"ディスク空き容量: {free_percent:.1f}%",
                "free_gb": round(free / (1024**3), 2),
                "total_gb": round(total / (1024**3), 2),
                "free_percent": round(free_percent, 1)
            }
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return {
                "status": "unknown",
                "message": f"ディスク容量チェックエラー: {str(e)}"
            }
    
    @staticmethod
    def check_memory() -> Dict[str, Any]:
        """メモリ使用量チェック"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            status = "healthy" if mem.percent < 80 else "warning" if mem.percent < 90 else "unhealthy"
            
            return {
                "status": status,
                "message": f"メモリ使用率: {mem.percent:.1f}%",
                "used_percent": round(mem.percent, 1),
                "available_gb": round(mem.available / (1024**3), 2),
                "total_gb": round(mem.total / (1024**3), 2)
            }
        except ImportError:
            return {
                "status": "unknown",
                "message": "psutilがインストールされていません"
            }
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return {
                "status": "unknown",
                "message": f"メモリチェックエラー: {str(e)}"
            }
    
    @staticmethod
    def check_sensors() -> Dict[str, Any]:
        """センサー接続チェック"""
        try:
            sensors = TemperatureQueries.get_all_latest()
            
            if len(sensors) == 0:
                return {
                    "status": "warning",
                    "message": "接続中のセンサーがありません",
                    "sensor_count": 0
                }
            
            # 最新データが5分以内かチェック
            from datetime import datetime, timedelta
            recent_count = 0
            for sensor in sensors:
                timestamp_str = sensor.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        if datetime.now() - timestamp < timedelta(minutes=5):
                            recent_count += 1
                    except:
                        pass
            
            status = "healthy" if recent_count > 0 else "warning"
            
            return {
                "status": status,
                "message": f"接続センサー数: {len(sensors)} (最新データ: {recent_count})",
                "sensor_count": len(sensors),
                "recent_count": recent_count
            }
        except Exception as e:
            logger.error(f"Sensor check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"センサーチェックエラー: {str(e)}"
            }
    
    @classmethod
    def check_all(cls) -> Dict[str, Any]:
        """全チェックを実行"""
        checks = {
            "database": cls.check_database(),
            "disk": cls.check_disk_space(),
            "memory": cls.check_memory(),
            "sensors": cls.check_sensors()
        }
        
        # 全体のステータスを決定
        statuses = [check.get("status") for check in checks.values()]
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": checks
        }

