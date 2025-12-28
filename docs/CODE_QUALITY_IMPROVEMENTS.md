# コード品質・パフォーマンス改善ガイド

**作成日:** 2025年12月27日  
**対象:** temperature_server / free_wifi  
**目標:** コード保守性・パフォーマンスの向上

---

## 目次

1. [コード品質問題](#コード品質問題)
2. [パフォーマンス最適化](#パフォーマンス最適化)
3. [リソース管理改善](#リソース管理改善)
4. [テスト戦略](#テスト戦略)

---

## コード品質問題

### 🔴 問題1: グローバル変数の乱用

#### 現在の状態

**ファイル:** `temperature_server/app/routes/dashboard.py`

```python
# ❌ グローバル変数の乱用
camera = None
camera_lock = threading.Lock()
camera_resolution = Config.AVAILABLE_RESOLUTIONS[Config.DEFAULT_RESOLUTION]
streaming_enabled = False

def get_camera():
    global camera
    with camera_lock:
        if camera is None or not camera.isOpened():
            # ...
            camera = cv2.VideoCapture(camera_index)
            return camera
```

#### 問題点

| 問題 | 影響 | 深刻度 |
|------|------|--------|
| グローバル状態が複数関数で変更される | デバッグが困難 | 🔴 高 |
| スレッドセーフでない部分がある | 競合状態のリスク | 🔴 高 |
| テストが困難 | 単体テスト不可 | 🟡 中 |

#### 改善策1: クラスに封装

```python
# 改善版: classes/camera_manager.py

import threading
import cv2
from typing import Optional
from logger import setup_logger

logger = setup_logger(__name__)

class CameraManager:
    """カメラ管理クラス（シングルトン）"""
    
    _instance: Optional['CameraManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance
    
    def _init(self):
        """初期化"""
        self.camera: Optional[cv2.VideoCapture] = None
        self.lock = threading.Lock()
        self.resolution = (1280, 720, 24)  # デフォルト
        self.is_streaming = False
    
    def get_camera(self) -> Optional[cv2.VideoCapture]:
        """カメラインスタンスを取得"""
        with self.lock:
            if self.camera is None or not self.camera.isOpened():
                self._init_camera()
            return self.camera
    
    def _init_camera(self):
        """カメラを初期化"""
        try:
            # デバイス検索...
            for i in range(0, 32):
                dev_path = f'/dev/video{i}'
                if os.path.exists(dev_path):
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            self.camera = cap
                            logger.info(f"✓ Camera initialized: {frame.shape}")
                            return
                    cap.release()
            
            logger.error("❌ No camera device found")
            self.camera = None
        
        except Exception as e:
            logger.error(f"❌ Camera init error: {e}")
            self.camera = None
    
    def release(self):
        """カメラをリリース"""
        with self.lock:
            if self.camera is not None:
                self.camera.release()
                self.camera = None
                logger.info("✓ Camera released")
    
    def start_streaming(self):
        """ストリーミングを開始"""
        with self.lock:
            self.is_streaming = True
    
    def stop_streaming(self):
        """ストリーミングを停止"""
        with self.lock:
            self.is_streaming = False
    
    def generate_frames(self):
        """フレーム生成ジェネレータ"""
        while self.is_streaming:
            cam = self.get_camera()
            if cam is None:
                yield None
                continue
            
            success, frame = cam.read()
            if not success:
                logger.warning("Frame read failed")
                continue
            
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                yield buffer.tobytes()

# 使用例
# from classes.camera_manager import CameraManager
# 
# manager = CameraManager()
# manager.start_streaming()
# for frame in manager.generate_frames():
#     # フレーム処理
# manager.stop_streaming()
# manager.release()
```

#### 改善策2: テスト可能な設計

```python
# tests/test_camera_manager.py

import unittest
from unittest.mock import patch, MagicMock
from classes.camera_manager import CameraManager

class TestCameraManager(unittest.TestCase):
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        manager = CameraManager()
        manager.release()
    
    @patch('cv2.VideoCapture')
    def test_camera_initialization(self, mock_capture):
        """カメラ初期化のテスト"""
        # Mock setup
        mock_cam = MagicMock()
        mock_cam.isOpened.return_value = True
        mock_cam.read.return_value = (True, MagicMock())
        mock_capture.return_value = mock_cam
        
        # Test
        manager = CameraManager()
        camera = manager.get_camera()
        
        # Assert
        self.assertIsNotNone(camera)
        mock_capture.assert_called()
    
    def test_streaming_state(self):
        """ストリーミング状態管理のテスト"""
        manager = CameraManager()
        
        # 初期状態: ストリーミング停止
        self.assertFalse(manager.is_streaming)
        
        # 開始
        manager.start_streaming()
        self.assertTrue(manager.is_streaming)
        
        # 停止
        manager.stop_streaming()
        self.assertFalse(manager.is_streaming)

if __name__ == '__main__':
    unittest.main()
```

---

### 🔴 問題2: 冗長な日時処理コード

#### 現在の状態

**ファイル:** `free_wifi/lib_utils.py`

```python
# ❌ 冗長で読みにくい
def get_zero_padding_text(value, digit):
    txt = ""
    txv = str(value)
    cnt = digit - len(txv)
    for i in range(cnt):
        txt += "0"
    txt += txv
    return txt

def get_datetime_text():
    now = datetime.now(T_JST)
    txt = ""
    txt += get_zero_padding_text(now.year, 4)
    txt += "-"
    txt += get_zero_padding_text(now.month, 2)
    # ... 長い
    return txt
```

#### 改善策

```python
# shared/utils/datetime_utils.py（改善版）

from datetime import datetime
import pytz

JST = pytz.timezone('Asia/Tokyo')

# 🆕 シンプルで読みやすい
def get_jst_now() -> datetime:
    """現在時刻をJSTで取得"""
    return datetime.now(JST)

def format_datetime(dt: datetime = None, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """日時をフォーマット"""
    if dt is None:
        dt = get_jst_now()
    return dt.strftime(fmt)

# 使用例
# now = get_jst_now()
# formatted = format_datetime(now)  # "2025-12-27 10:30:45"
```

**コード削減: 53行 → 15行 ⚡**

---

### 🟡 問題3: エラーハンドリングの不統一

#### 現在の状態

**temperature_server/app/routes/api.py:**
```python
try:
    # 処理
    return success_response(data)
except Exception as e:
    return handle_error(str(e), 500)
```

**temperature_server/services/wifi_manager.py:**
```python
try:
    # 処理
    return True
except Exception as e:
    logger.error(f"Error: {e}")
    return False
```

**free_wifi/main.py:**
```python
try:
    # 処理
except Exception as e:
    messagebox.showerror("エラー", str(e))
```

#### 問題点

- 統一されたエラーハンドリングがない
- エラー情報が失われることもある
- テストが困難

#### 改善策

```python
# shared/exceptions.py

class BaseApplicationException(Exception):
    """アプリケーション基本例外"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }

class WiFiException(BaseApplicationException):
    """WiFi 関連エラー"""
    pass

class TemperatureSensorException(BaseApplicationException):
    """温度センサー関連エラー"""
    pass

class ValidationException(BaseApplicationException):
    """バリデーションエラー"""
    pass

# 統一されたエラーハンドラー
from functools import wraps
from flask import jsonify

def handle_exceptions(f):
    """例外をハンドルするデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except BaseApplicationException as e:
            logger.warning(f"Application error: {e.error_code} - {e.message}")
            return jsonify({
                "status": "error",
                **e.to_dict()
            }), 400
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred"
            }), 500
    
    return decorated_function

# 使用例
@api_bp.route('/temperature', methods=['POST'])
@handle_exceptions
def receive_temperature():
    data = request.get_json()
    
    # バリデーション
    valid, msg = validate_sensor_id(data.get('sensor_id'))
    if not valid:
        raise ValidationException(msg, error_code='INVALID_SENSOR_ID')
    
    # 処理...
    return success_response({"received": True})
```

---

## パフォーマンス最適化

### 🟡 問題4: データベース接続の最適化

#### 現在の状態

```python
# ❌ 毎回新しい接続を開く
def get_latest_reading(sensor_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ...")
        result = cursor.fetchone()
        conn.close()  # 毎回クローズ
        return result
```

#### 改善策: 接続プーリング

```python
# shared_resources/database/connection_pool.py

import sqlite3
import threading
from typing import Optional
from contextlib import contextmanager

class ConnectionPool:
    """SQLite 接続プール"""
    
    def __init__(self, database: str, pool_size: int = 5):
        self.database = database
        self.pool_size = pool_size
        self.connections = []
        self.lock = threading.Lock()
        self._init_pool()
    
    def _init_pool(self):
        """コネクションプールを初期化"""
        for _ in range(self.pool_size):
            conn = sqlite3.connect(
                self.database,
                check_same_thread=False,
                timeout=10
            )
            conn.row_factory = sqlite3.Row
            self.connections.append(conn)
    
    @contextmanager
    def get_connection(self):
        """コネクションを取得（context manager）"""
        with self.lock:
            while not self.connections:
                # コネクション利用可能まで待機
                self.lock.release()
                import time
                time.sleep(0.1)
                self.lock.acquire()
            
            conn = self.connections.pop()
        
        try:
            yield conn
        finally:
            with self.lock:
                self.connections.append(conn)
    
    def close_all(self):
        """全コネクションをクローズ"""
        for conn in self.connections:
            conn.close()
        self.connections.clear()

# 使用例
# pool = ConnectionPool('temperature.db')
#
# with pool.get_connection() as conn:
#     cursor = conn.cursor()
#     cursor.execute("SELECT ...")
#     result = cursor.fetchone()
```

### 🟡 問題5: ログファイルローテーションの最適化

#### 現在の状態

```python
# ❌ ファイルサイズ制限のみ
LOG_MAX_BYTES = 10485760  # 10MB
LOG_BACKUP_COUNT = 5      # ❌ 古いログが蓄積
```

#### 改善策: 時間ベースのローテーション

```python
# shared/logging/logger.py（改善版）

import logging.handlers
from datetime import datetime

class DualRotatingHandler(logging.handlers.RotatingFileHandler):
    """時間 + サイズベースのローテーション"""
    
    def __init__(self, filename, when='midnight', interval=1, 
                 maxBytes=10485760, backupCount=7):
        # TimedRotatingFileHandler の機能を使用
        # 日次ローテーション + サイズ制限
        
        # TimedRotatingFileHandler ベースに拡張
        self.when = when
        self.interval = interval
        self.backupCount = backupCount
        
        super().__init__(filename, maxBytes=maxBytes, backupCount=backupCount)
    
    def shouldRollover(self, record):
        """ローテーション判定"""
        # サイズチェック
        if super().shouldRollover(record):
            return True
        
        # 時間チェック（毎日00:00にローテーション）
        if self.when == 'midnight':
            now = datetime.now()
            if now.hour == 0 and now.minute == 0:
                return True
        
        return False

# 使用例
# handler = DualRotatingHandler(
#     'app.log',
#     when='midnight',
#     maxBytes=10485760,  # 10MB
#     backupCount=7       # 7日分保持
# )
```

---

## リソース管理改善

### 🟡 問題6: メモリリークのリスク

#### 現在の状態

**ファイル:** `free_wifi/main.py`

```python
# ❌ 上限なくメモリ使用量が増加
self.web_driver = webdriver.Chrome(...)

# gc.collect() は呼ばれるがタイミング不明確
gc.collect()
```

#### 改善策: 明示的なリソース管理

```python
# 改善版: classes/resource_manager.py

import weakref
import gc
from typing import List

class ResourceManager:
    """リソース管理（キャッシング、GC）"""
    
    def __init__(self, memory_threshold_mb: int = 100):
        self.resources: List[weakref.ref] = []
        self.memory_threshold_mb = memory_threshold_mb
    
    def register_resource(self, resource):
        """リソースを登録"""
        self.resources.append(weakref.ref(resource))
        self._check_memory()
    
    def _check_memory(self):
        """メモリ使用量をチェック"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > self.memory_threshold_mb:
            logger.warning(f"⚠️  Memory usage high: {memory_mb:.1f}MB")
            
            # 無効な参照を削除
            self.resources = [
                ref for ref in self.resources 
                if ref() is not None
            ]
            
            # ガベージコレクション
            gc.collect()
            
            memory_mb = process.memory_info().rss / 1024 / 1024
            logger.info(f"✓ Memory cleaned: {memory_mb:.1f}MB")
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        for ref in self.resources:
            resource = ref()
            if resource is not None:
                if hasattr(resource, 'quit'):
                    resource.quit()
                elif hasattr(resource, 'close'):
                    resource.close()
        
        self.resources.clear()
        gc.collect()

# 使用例
# manager = ResourceManager(memory_threshold_mb=200)
# manager.register_resource(web_driver)
# ...
# manager.cleanup()
```

---

## テスト戦略

### 🟢 テストフレームワーク

#### 構成

```
raspberry_pi/
├── temperature_server/tests/
│   ├── test_config.py
│   ├── test_api.py
│   ├── test_database.py
│   └── test_integration.py
├── free_wifi/tests/
│   ├── test_config.py
│   ├── test_main.py
│   └── test_selenium.py
└── shared/tests/
    ├── test_logging.py
    ├── test_validators.py
    └── test_datetime_utils.py
```

#### テスト例

**ファイル:** `shared/tests/test_validators.py`

```python
import unittest
from shared.utils.validators import (
    validate_sensor_id,
    validate_temperature
)

class TestValidators(unittest.TestCase):
    
    def test_valid_sensor_id(self):
        """有効なセンサーID"""
        valid, msg = validate_sensor_id("sensor_1")
        self.assertTrue(valid)
        self.assertEqual(msg, "")
    
    def test_invalid_sensor_id_length(self):
        """長すぎるセンサーID"""
        long_id = "a" * 100
        valid, msg = validate_sensor_id(long_id)
        self.assertFalse(valid)
        self.assertIn("too long", msg)
    
    def test_invalid_sensor_id_format(self):
        """形式が不正なセンサーID"""
        valid, msg = validate_sensor_id("sensor@invalid")
        self.assertFalse(valid)
        self.assertIn("alphanumeric", msg)
    
    def test_valid_temperature(self):
        """有効な温度値"""
        valid, msg = validate_temperature(25.5)
        self.assertTrue(valid)
    
    def test_invalid_temperature_out_of_range(self):
        """範囲外の温度値"""
        valid, msg = validate_temperature(200)
        self.assertFalse(valid)
        self.assertIn("out of range", msg)
    
    def test_invalid_temperature_type(self):
        """型が不正な温度値"""
        valid, msg = validate_temperature("not_a_number")
        self.assertFalse(valid)
        self.assertIn("must be numeric", msg)

if __name__ == '__main__':
    unittest.main()
```

#### テスト実行

```bash
# 全テストを実行
python -m pytest

# カバレッジ付き実行
python -m pytest --cov=. --cov-report=html

# 特定のテストを実行
python -m pytest shared/tests/test_validators.py
```

---

## チェックリスト

### コード品質

- [ ] グローバル変数をクラスに封装
- [ ] エラーハンドリングを統一
- [ ] 日時処理を共有モジュール化
- [ ] テストを実装（カバレッジ > 80%）

### パフォーマンス

- [ ] データベース接続プールを導入
- [ ] ログローテーションを最適化
- [ ] メモリリークをテスト

### リソース管理

- [ ] リソース管理クラスを実装
- [ ] デストラクタを確認

---

**最終更新:** 2025年12月27日
