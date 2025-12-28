"""
ユーティリティ関数モジュール
main.py で使用される日時処理関数を提供します
"""

from datetime import datetime


def get_datetime_text():
    """
    現在の日時を 'YYYY-MM-DD HH:MM:SS' 形式で返す
    
    Returns:
        str: 現在の日時文字列（例: '2025-12-28 13:10:45'）
    """
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def get_time_text():
    """
    現在の時刻を 'HH:MM:SS' 形式で返す
    
    Returns:
        str: 現在の時刻文字列（例: '13:10:45'）
    """
    return datetime.now().strftime('%H:%M:%S')
