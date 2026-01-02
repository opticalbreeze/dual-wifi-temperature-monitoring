"""
設定ファイル
必要な設定値をここに定義します
"""

import os
from pathlib import Path

# プロジェクトのルートディレクトリ
PROJECT_ROOT = Path(__file__).parent.resolve()

# ログ設定
ENABLE_DEBUG_LOG = True          # デバッグログを出力する場合はTrue
ENABLE_TRACEMALLOC_LOG = False   # メモリ割当量を出力する場合はTrue
ENABLE_STDOUT_LOG = True         # ログを標準出力に表示する場合はTrue
MAX_LINES_LOG = 1000             # ログ表示行数最大値

# タイマー設定（秒）
INTERVAL_ALIVE = 5 * 60          # インターネット接続確認周期
INTERVAL_TRACEMALLOC = 30 * 60   # メモリ使用量表示周期
INTERVAL_WEBDRIVER = 12 * 3600   # Webドライバー更新周期

# Webドライバー設定
# Raspbian（ラズビアン）の場合、chromedriverは以下のパスにある可能性があります
# インストール方法によって異なる場合があります
WEBDRIVER_PATHS = [
    "/usr/bin/chromedriver",      # 標準のインストール先
    "/usr/lib/chromium-browser/chromedriver",  # Chromiumと一緒にインストールされた場合
    str(PROJECT_ROOT / "chromedriver"),  # プロジェクトディレクトリ内
]

def get_webdriver_path():
    """利用可能なWebドライバーのパスを返す"""
    for path in WEBDRIVER_PATHS:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    return WEBDRIVER_PATHS[0]  # デフォルト値

# テストページURL
TEST_PAGE_URL = "http://example.com"
TEST_PAGE_CURRENT_URL = "https://example.com/"

# フォント設定
# Raspbian（ラズビアン）で利用可能なフォント（優先順位順）
MONO_FONT_FAMILY = "DejaVu Sans Mono"  # 第1候補
MONO_FONT_FALLBACK = ["Liberation Mono", "Courier", "monospace"]  # フォールバック

# GUI設定
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
WINDOW_TITLE = "Guest2-Repeater"

