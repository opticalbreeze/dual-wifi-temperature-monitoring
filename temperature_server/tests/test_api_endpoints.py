"""
APIエンドポイントの統合テスト
Flaskアプリケーションのテストクライアントを使用
"""

import unittest
import sys
import json
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from database.models import init_database


class TestAPIEndpoints(unittest.TestCase):
    """APIエンドポイントの統合テスト"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラスのセットアップ"""
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        # テスト用データベースの初期化
        init_database()
    
    def test_receive_temperature_valid(self):
        """正常な温度データの送信"""
        data = {
            "device_id": "TEST_SENSOR",
            "temperature": 25.5,
            "name": "テストセンサー"
        }
        response = self.client.post(
            '/api/temperature',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        json_data = json.loads(response.data)
        self.assertEqual(json_data['status'], 'success')
        self.assertEqual(json_data['temperature'], 25.5)
        self.assertEqual(json_data['device_id'], 'TEST_SENSOR')
    
    def test_receive_temperature_invalid_content_type(self):
        """無効なContent-Type"""
        data = {
            "device_id": "TEST_SENSOR",
            "temperature": 25.5
        }
        response = self.client.post(
            '/api/temperature',
            data=json.dumps(data),
            content_type='text/plain'
        )
        self.assertEqual(response.status_code, 400)
        json_data = json.loads(response.data)
        self.assertEqual(json_data['status'], 'error')
    
    def test_receive_temperature_invalid_json(self):
        """無効なJSON"""
        response = self.client.post(
            '/api/temperature',
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        json_data = json.loads(response.data)
        self.assertEqual(json_data['status'], 'error')
    
    def test_receive_temperature_missing_fields(self):
        """必須フィールドが欠けている"""
        data = {
            "device_id": "TEST_SENSOR"
            # temperatureが欠けている
        }
        response = self.client.post(
            '/api/temperature',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        json_data = json.loads(response.data)
        self.assertEqual(json_data['status'], 'error')
    
    def test_receive_temperature_out_of_range(self):
        """温度が範囲外"""
        data = {
            "device_id": "TEST_SENSOR",
            "temperature": 1000.0  # 範囲外
        }
        response = self.client.post(
            '/api/temperature',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        json_data = json.loads(response.data)
        self.assertEqual(json_data['status'], 'error')
        self.assertIn('out of valid range', json_data['message'])
    
    def test_get_all_sensors(self):
        """全センサー取得"""
        response = self.client.get('/api/sensors')
        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.data)
        self.assertEqual(json_data['status'], 'success')
        self.assertIn('sensors', json_data)
        self.assertIn('count', json_data)
    
    def test_get_sensor_data_valid(self):
        """特定センサーのデータ取得（正常）"""
        # まずデータを送信
        data = {
            "device_id": "TEST_SENSOR_01",
            "temperature": 25.5
        }
        self.client.post(
            '/api/temperature',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # データを取得
        response = self.client.get('/api/temperature/TEST_SENSOR_01?hours=1')
        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.data)
        self.assertEqual(json_data['status'], 'success')
        self.assertEqual(json_data['sensor_id'], 'TEST_SENSOR_01')
        self.assertIn('readings', json_data)
        self.assertIn('statistics', json_data)
    
    def test_get_sensor_data_invalid_hours(self):
        """無効なhoursパラメータ"""
        response = self.client.get('/api/temperature/TEST_SENSOR?hours=10000')
        self.assertEqual(response.status_code, 400)
        json_data = json.loads(response.data)
        self.assertEqual(json_data['status'], 'error')
    
    def test_get_status(self):
        """システムステータス取得"""
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.data)
        self.assertEqual(json_data['status'], 'success')
        self.assertIn('timestamp', json_data)
        self.assertIn('connected_sensors', json_data)
        self.assertIn('memory_usage_percent', json_data)
        self.assertIn('disk_usage_percent', json_data)


if __name__ == '__main__':
    unittest.main()

