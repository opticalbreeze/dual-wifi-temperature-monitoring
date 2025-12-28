# 統合アーキテクチャ改善ガイド

**作成日:** 2025年12月27日  
**対象:** temperature_server と free_wifi の統合  
**目的:** 2つのプロジェクトを1つの統合システムとして運用可能にする

---

## 目次

1. [現状分析](#現状分析)
2. [統合戦略](#統合戦略)
3. [実装アーキテクチャ](#実装アーキテクチャ)
4. [段階的実装計画](#段階的実装計画)
5. [マイグレーションガイド](#マイグレーションガイド)

---

## 現状分析

### 問題点

#### 🔴 **問題1: 設定の分散化**

| 項目 | temperature_server | free_wifi | 現状 |
|------|-------------------|-----------|------|
| Flask設定 | `config.py` | N/A | 分散 |
| WiFi設定 | `config.py` | `config.py` | **重複** |
| ロギング設定 | `logger.py` | `main.py` | **重複** |
| タイムゾーン | `pytz` + `queries.py` | `lib_utils.py` | **重複** |
| 環境変数 | `os.getenv()` | `os.getenv()` | **不統一** |

#### 🔴 **問題2: コードの重複**

```python
# free_wifi/lib_utils.py (53行)
def get_zero_padding_text(value, digit):
    txt = ""
    txv = str(value)
    cnt = digit - len(txv)
    for i in range(cnt):
        txt += "0"
    txt += txv
    return txt

# 改善提案: f"{value:0{digit}d}" で十分
```

#### 🔴 **問題3: 依存関係が不明確**

```
temperature_server/
  ├── requires: Flask, opencv, psutil, ...
  
free_wifi/
  ├── requires: selenium, tkinter, ...
  
❌ どちらが先に起動すべき？
❌ API間の連携がない
❌ 共通リソース（WiFi）の競合処理がない
```

#### 🔴 **問題4: リソース管理の欠如**

- WiFi設定（AP/Station）が2つのプロジェクトで独立
- ログファイルが別々のディレクトリに生成
- データベース接続がプロジェクト毎に分離

---

## 統合戦略

### 🎯 目標

```
統合前:
├─ temperature_server (Flask)
└─ free_wifi (Tkinter + Selenium)
   ❌ 独立運用・連携なし

統合後:
├─ shared/ (共通モジュール)
│  ├─ config/    (統一設定)
│  ├─ logging/   (統一ロギング)
│  ├─ utils/     (共通ユーティリティ)
│  └─ exceptions/ (統一例外)
├─ temperature_server/ (改善版)
│  └─ config.py → shared.config をimport
└─ free_wifi/ (改善版)
   └─ config.py → shared.config をimport
✅ 統一管理・効率的な連携
```

### 📊 メリット

| メリット | 効果 |
|---------|------|
| **設定の一元管理** | 本番環境対応が容易 |
| **コードの重複排除** | 保守性向上、バグ減少 |
| **リソース共有** | 効率化、競合回避 |
| **統一したエラー処理** | デバッグが容易 |
| **バージョン管理の簡素化** | デプロイが安全 |

---

## 実装アーキテクチャ

### 新ディレクトリ構成

```
raspberry_pi/
│
├── shared/                          # 🆕 共通モジュール
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── base.py                 # 基本設定（環境変数管理）
│   │   ├── security.py             # セキュリティ設定
│   │   ├── wifi.py                 # WiFi設定（統合）
│   │   └── logging_config.py       # ロギング設定（統合）
│   ├── logging/
│   │   ├── __init__.py
│   │   ├── logger.py               # 統一ログマネージャー
│   │   └── filters.py              # ログフィルター
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── datetime_utils.py       # 日時処理（統合）
│   │   ├── validators.py           # バリデーション共有
│   │   └── constants.py            # 共通定数
│   └── exceptions.py               # 統一例外定義
│
├── temperature_server/
│   ├── config.py                   # shared.config をimport
│   ├── run.py
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py            # shared設定を使用
│   │   ├── flask_app.py
│   │   ├── exceptions.py           # → shared.exceptions に統合可能
│   │   ├── routes/
│   │   │   ├── api.py             # shared.utils.validators 使用
│   │   │   ├── dashboard.py
│   │   │   └── wifi.py
│   │   └── static/
│   ├── database/
│   │   ├── models.py
│   │   └── queries.py
│   ├── services/
│   │   ├── wifi_manager.py        # 統合WiFiマネージャーを使用
│   │   └── background_tasks.py
│   ├── systemd/
│   └── tests/
│
├── free_wifi/
│   ├── config.py                   # shared.config をimport
│   ├── main.py                     # shared.logging 使用
│   ├── lib_utils.py                # → shared.utils へ統合
│   ├── requirements.txt
│   ├── tests/
│   └── ファイル/
│
├── shared_resources/               # 🆕 共有リソース
│   ├── services/
│   │   └── unified_wifi_manager.py # 統合WiFi管理（新規）
│   └── models/
│       └── unified_models.py       # 共有データモデル（新規）
│
├── docs/
│   ├── SECURITY_IMPROVEMENTS.md    # セキュリティ改善提案
│   ├── INTEGRATION_GUIDE.md        # このドキュメント
│   └── ...
│
├── .env.template
├── .env                            # 🔒 Git除外
├── .gitignore
├── requirements-all.txt            # 全依存関係（統合版）
└── README.md
```

---

## 共有モジュール実装例

### 1. 統一設定モジュール

**ファイル:** `shared/config/base.py`

```python
"""
shared/config/base.py
全プロジェクト共通の設定
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env ファイルを読み込み
env_file = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_file)

class BaseConfig:
    """基本設定"""
    
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    LOGS_DIR = PROJECT_ROOT / 'logs'
    DATA_DIR = PROJECT_ROOT / 'data'
    
    # ===== 環境 =====
    ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # ===== セキュリティ =====
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY or SECRET_KEY == 'dev-secret-key-change-in-production':
        raise ValueError("SECRET_KEY must be set in .env")
    
    # ===== ロギング =====
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_MAX_BYTES = 10485760  # 10MB
    LOG_BACKUP_COUNT = 5
    LOG_RETENTION_DAYS = 7
    
    # ===== タイムゾーン =====
    TIMEZONE = 'Asia/Tokyo'
    
    @classmethod
    def validate(cls):
        """設定の検証"""
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)

class DevelopmentConfig(BaseConfig):
    """開発環境設定"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(BaseConfig):
    """本番環境設定"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'

# 環境に応じた設定を選択
if BaseConfig.ENV == 'development':
    Config = DevelopmentConfig
else:
    Config = ProductionConfig

# 起動時に検証
Config.validate()
```

**ファイル:** `shared/config/wifi.py`

```python
"""
shared/config/wifi.py
WiFi統一設定（AP + Station）
"""

import os
from shared.config.base import Config

class WiFiConfig:
    """WiFi設定（2つのプロジェクト共有）"""
    
    # ===== AP モード（ESP32接続用）=====
    AP_INTERFACE = 'wlan1'          # USB WiFi アダプタ
    AP_SSID = os.getenv('AP_SSID', 'RaspberryPi_Temperature')
    AP_PASSWORD = os.getenv('AP_PASSWORD')
    AP_IP = '192.168.4.1'
    AP_SUBNET = '192.168.4.0/24'
    AP_DHCP_START = '192.168.4.2'
    AP_DHCP_END = '192.168.4.254'
    
    # ===== Station モード（インターネット接続用）=====
    STATION_INTERFACE = 'wlan0'     # オンボード WiFi
    
    # ===== WiFi 監視 =====
    WIFI_CHECK_INTERVAL = 600       # 10分毎
    WIFI_RETRY_ATTEMPTS = 3
    WIFI_RETRY_DELAY = 10
    
    # バリデーション
    if not AP_PASSWORD or len(AP_PASSWORD) < 8:
        raise ValueError("AP_PASSWORD must be set and >= 8 characters in .env")
```

### 2. 統一ロギングモジュール

**ファイル:** `shared/logging/logger.py`

```python
"""
shared/logging/logger.py
統一ロギングシステム
"""

import logging
import logging.handlers
from pathlib import Path
from shared.config.base import Config

class UnifiedLogger:
    """統一ログマネージャー"""
    
    _loggers = {}
    
    @staticmethod
    def get_logger(name, module_type='service'):
        """ロガーを取得（シングルトン）"""
        
        if name in UnifiedLogger._loggers:
            return UnifiedLogger._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(logging.getLevelName(Config.LOG_LEVEL))
        
        # ファイルハンドラ
        log_file = Config.LOGS_DIR / f'{name}.log'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.handlers.RotatingFileHandler(
            str(log_file),
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        
        # フォーマッタ
        if Config.DEBUG:
            fmt = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        else:
            fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        formatter = logging.Formatter(fmt)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # コンソールハンドラ（開発環境のみ）
        if Config.DEBUG:
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            logger.addHandler(console)
        
        UnifiedLogger._loggers[name] = logger
        return logger

# 使用例
# logger = UnifiedLogger.get_logger(__name__)
```

### 3. 統一ユーティリティ

**ファイル:** `shared/utils/datetime_utils.py`

```python
"""
shared/utils/datetime_utils.py
日時処理（統一・最適化）
"""

from datetime import datetime, timezone, timedelta
import pytz

# タイムゾーン定義
JST = pytz.timezone('Asia/Tokyo')

def get_jst_now():
    """現在時刻をJSTで取得"""
    return datetime.now(JST)

def format_jst_datetime(dt=None):
    """日時を "YYYY-MM-DD HH:MM:SS" 形式でフォーマット"""
    if dt is None:
        dt = get_jst_now()
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def format_time(dt=None):
    """時刻を "HH:MM:SS" 形式でフォーマット"""
    if dt is None:
        dt = get_jst_now()
    return dt.strftime('%H:%M:%S')

# 使用例
# from shared.utils.datetime_utils import get_jst_now, format_jst_datetime
# now = get_jst_now()
# formatted = format_jst_datetime(now)  # "2025-12-27 10:30:45"
```

**ファイル:** `shared/utils/validators.py`

```python
"""
shared/utils/validators.py
バリデーション関数（統一）
"""

import re
from typing import Tuple, Any

def validate_sensor_id(sensor_id: str, max_length: int = 50) -> Tuple[bool, str]:
    """
    センサーID を検証
    
    Returns:
        (is_valid, error_message)
    """
    if not sensor_id or not isinstance(sensor_id, str):
        return False, "sensor_id must be a non-empty string"
    
    if len(sensor_id) > max_length:
        return False, f"sensor_id too long (max {max_length} chars)"
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', sensor_id):
        return False, "sensor_id must contain only alphanumeric, dash, and underscore"
    
    return True, ""

def validate_temperature(temp: float, min_val: float = -50, max_val: float = 150) -> Tuple[bool, str]:
    """
    温度値を検証
    
    Returns:
        (is_valid, error_message)
    """
    try:
        temp = float(temp)
    except (ValueError, TypeError):
        return False, f"temperature must be numeric, got {type(temp).__name__}"
    
    if not (min_val <= temp <= max_val):
        return False, f"temperature out of range ({min_val}~{max_val}°C)"
    
    return True, ""

# 使用例
# from shared.utils.validators import validate_sensor_id, validate_temperature
# valid, msg = validate_sensor_id("sensor_1")
# valid, msg = validate_temperature(25.5)
```

---

## 段階的実装計画

### 📅 Phase 1: 基盤構築（Week 1-2）

#### タスク

- [ ] `shared/` ディレクトリ構造を作成
- [ ] `shared/config/base.py` を実装
- [ ] `shared/logging/logger.py` を実装
- [ ] `.env.template` を作成
- [ ] `requirements-all.txt` を作成

#### 成果物

```
shared/
├── config/
│   ├── __init__.py
│   └── base.py          ✅
├── logging/
│   ├── __init__.py
│   └── logger.py        ✅
├── utils/
│   ├── __init__.py
│   ├── datetime_utils.py
│   ├── validators.py
│   └── constants.py
└── exceptions.py
```

### 📅 Phase 2: マイグレーション（Week 3-4）

#### temperature_server

- [ ] `config.py` を shared.config をimport するように修正
- [ ] `logger.py` を削除 → `UnifiedLogger` を使用に変更
- [ ] `app/__init__.py` で統一設定を使用
- [ ] テスト実行・動作確認

#### free_wifi

- [ ] `config.py` を shared.config をimport するように修正
- [ ] `lib_utils.py` を削除 → `shared.utils` を使用に変更
- [ ] ロギングを `UnifiedLogger` に統一
- [ ] テスト実行・動作確認

### 📅 Phase 3: 統合機能追加（Week 5-6）

#### 新規モジュール

- [ ] `shared_resources/services/unified_wifi_manager.py` を実装
- [ ] WiFi リソース競合の回避メカニズムを実装
- [ ] API間通信の定義（如何にしてtemperature_serverとfree_wifiが通信するか）

#### テスト

- [ ] 統合テストを実装
- [ ] 本番環境シミュレーション

### 📅 Phase 4: 本番化（Week 7+）

- [ ] セキュリティレビュー
- [ ] パフォーマンステスト
- [ ] ドキュメント完成
- [ ] 本番デプロイ

---

## マイグレーションガイド

### STEP 1: temperature_server を修正

#### 1.1 `config.py` を修正

**変更前:**
```python
import os
from pathlib import Path

class Config:
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    ...
```

**変更後:**
```python
from shared.config.base import Config as BaseConfig
from shared.config.wifi import WiFiConfig

class Config(BaseConfig):
    """temperature_server 専用設定"""
    
    # Flask
    FLASK_HOST = '0.0.0.0'
    FLASK_PORT = 5000
    
    # WiFi（shared.config から継承）
    AP_SSID = WiFiConfig.AP_SSID
    AP_PASSWORD = WiFiConfig.AP_PASSWORD
    AP_INTERFACE = WiFiConfig.AP_INTERFACE
    ...
```

#### 1.2 `logger.py` を削除・置き換え

**変更前:**
```python
def setup_logger(name):
    logger = logging.getLogger(name)
    ...
```

**変更後:**
```python
from shared.logging.logger import UnifiedLogger

def setup_logger(name):
    return UnifiedLogger.get_logger(name)
```

#### 1.3 `app/__init__.py` を修正

```python
from shared.logging.logger import UnifiedLogger

logger = UnifiedLogger.get_logger(__name__)

def create_app():
    from config import Config
    
    app = Flask(__name__)
    app.config.from_object(Config)
    ...
```

#### 1.4 `app/routes/api.py` を修正

```python
from shared.utils.validators import validate_sensor_id, validate_temperature

def validate_temperature_request(data):
    # sensor_id の検証
    valid, msg = validate_sensor_id(data.get('sensor_id'))
    if not valid:
        return False, msg
    
    # temperature の検証
    valid, msg = validate_temperature(data.get('temperature'))
    if not valid:
        return False, msg
    
    ...
```

### STEP 2: free_wifi を修正

#### 2.1 `config.py` を修正

```python
from shared.config.base import Config as BaseConfig
from shared.config.wifi import WiFiConfig

class Config(BaseConfig):
    """free_wifi 専用設定"""
    
    # WiFi（shared から継承）
    AP_SSID = WiFiConfig.AP_SSID
    AP_PASSWORD = WiFiConfig.AP_PASSWORD
    ...
```

#### 2.2 `lib_utils.py` を削除・置き換え

```python
from shared.utils.datetime_utils import get_jst_now, format_jst_datetime, format_time

# lib_utils の関数を以下に置き換え
# get_zero_padding_text() → f"{value:0{digit}d}"
# get_datetime_text() → format_jst_datetime()
# get_time_text() → format_time()
```

#### 2.3 `main.py` のロギングを修正

```python
from shared.logging.logger import UnifiedLogger

logger = UnifiedLogger.get_logger(__name__)
```

### STEP 3: テスト

#### テストスクリプト

```bash
#!/bin/bash
# test_integration.sh

echo "=== Testing shared config ==="
python3 -c "from shared.config.base import Config; print('✓ BaseConfig loaded')"

echo "=== Testing WiFi config ==="
python3 -c "from shared.config.wifi import WiFiConfig; print(f'✓ WiFiConfig: AP_SSID={WiFiConfig.AP_SSID}')"

echo "=== Testing unified logger ==="
python3 -c "from shared.logging.logger import UnifiedLogger; logger = UnifiedLogger.get_logger('test'); logger.info('✓ Unified logger works')"

echo "=== Testing temperature_server ==="
cd temperature_server
python3 -c "from config import Config; print('✓ temperature_server config loaded')"

echo "=== Testing free_wifi ==="
cd ../free_wifi
python3 -c "from config import Config; print('✓ free_wifi config loaded')"

echo "All tests passed! ✅"
```

---

## 実装チェックリスト

### Phase 1: 基盤構築

- [ ] `shared/config/base.py` 実装完了
- [ ] `shared/config/wifi.py` 実装完了
- [ ] `shared/logging/logger.py` 実装完了
- [ ] `shared/utils/datetime_utils.py` 実装完了
- [ ] `shared/utils/validators.py` 実装完了
- [ ] `.env.template` 作成完了
- [ ] `.gitignore` に `.env` を追加確認

### Phase 2: マイグレーション

#### temperature_server

- [ ] `config.py` 修正完了
- [ ] `logger.py` 削除・置き換え完了
- [ ] `app/__init__.py` 修正完了
- [ ] `app/routes/api.py` 修正完了
- [ ] ローカルテスト成功 ✓

#### free_wifi

- [ ] `config.py` 修正完了
- [ ] `lib_utils.py` 削除・置き換え完了
- [ ] `main.py` ロギング修正完了
- [ ] ローカルテスト成功 ✓

### Phase 3: 統合テスト

- [ ] 2つのプロジェクトが同時起動可能
- [ ] 共有リソース（WiFi）が競合していない
- [ ] ログが統一されている
- [ ] 環境変数が正しく読み込まれている

---

**最終更新:** 2025年12月27日
