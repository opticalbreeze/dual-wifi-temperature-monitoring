"""
temperature_server/app/routes/dashboard.py
ダッシュボードルート
"""

from flask import Blueprint, render_template, Response, request, jsonify
from logger import setup_logger
import sys
from pathlib import Path
import threading
import time

# パス設定
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger = setup_logger(__name__)
dashboard_bp = Blueprint('dashboard', __name__)

# グローバル状態管理
_camera_state = {
    'resolution': (1280, 720),
    'fps': 30,
    'lock': threading.Lock(),
    'stop_event': threading.Event(),
}

@dashboard_bp.route('/')
def index():
    """ダッシュボードホームページ"""
    return render_template('dashboard.html')

@dashboard_bp.route('/stream')
def stream():
    """ビデオストリーミングページ"""
    return render_template('stream.html')

@dashboard_bp.route('/management')
def management():
    """管理画面ページ"""
    return render_template('management.html')

@dashboard_bp.route('/video_feed')
def video_feed():
    """ビデオフィード（MJPEGストリーム）"""
    try:
        import cv2
        import io
        
        # カメラを初期化（デバイス0 = 最初のカメラ）
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("カメラを開くことができません")
            return "Error: カメラが見つかりません", 500
        
        def generate_frames():
            """フレームジェネレータ"""
            frame_count = 0
            last_width, last_height, last_fps = None, None, None
            jpeg_quality = 80  # 品質設定（毎回変更しない）
            
            try:
                while not _camera_state['stop_event'].is_set():
                    # 解像度・FPS設定が変わった時のみ更新（毎フレーム確認は避ける）
                    with _camera_state['lock']:
                        width, height = _camera_state['resolution']
                        fps = _camera_state['fps']
                    
                    if (width, height, fps) != (last_width, last_height, last_fps):
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                        cap.set(cv2.CAP_PROP_FPS, fps)
                        last_width, last_height, last_fps = width, height, fps
                        logger.info(f"カメラ設定更新: {width}x{height}, {fps}FPS")
                    
                    ret, frame = cap.read()
                    if not ret:
                        continue  # スキップ（sleep削除）
                    
                    # JPEGエンコード
                    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
                    if not ret:
                        continue  # スキップ
                    
                    frame_bytes = buffer.tobytes()
                    
                    # MJPEGストリーム形式で返す
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n'
                           b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
                           b'\r\n' + frame_bytes + b'\r\n')
                    
                    frame_count += 1
            except Exception as e:
                logger.error(f"ビデオフィード生成エラー: {e}")
            finally:
                cap.release()
                _camera_state['stop_event'].clear()
        
        logger.info("ビデオフィード開始")
        return Response(
            generate_frames(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    except ImportError:
        logger.error("OpenCV（cv2）がインストールされていません")
        return "Error: OpenCVがインストールされていません", 500
    except Exception as e:
        logger.error(f"ビデオフィードエラー: {e}")
        return f"Error: {str(e)}", 500

@dashboard_bp.route('/video_feed/stop', methods=['GET', 'POST'])
def stop_video_feed():
    """ビデオフィード停止"""
    with _camera_state['lock']:
        _camera_state['stop_event'].set()
    logger.info("ビデオフィード停止リクエスト")
    return jsonify({'status': 'stopped'})


@dashboard_bp.route('/video_feed/resolution', methods=['POST'])
def change_resolution():
    """解像度変更エンドポイント"""
    try:
        data = request.get_json()
        if not data or 'resolution' not in data:
            return jsonify({'status': 'error', 'message': '解像度が指定されていません'}), 400
        
        resolution_str = data['resolution']
        
        # 解像度マッピング
        resolution_map = {
            '360p': (640, 360),
            '720p': (1280, 720),
            '1080p': (1920, 1080),
        }
        
        if resolution_str not in resolution_map:
            return jsonify({'status': 'error', 'message': '無効な解像度です'}), 400
        
        new_resolution = resolution_map[resolution_str]
        
        # 既存ストリームを停止
        with _camera_state['lock']:
            _camera_state['stop_event'].set()
            time.sleep(0.5)  # フレーム生成を停止させる時間
            
            # 解像度を更新
            _camera_state['resolution'] = new_resolution
            _camera_state['stop_event'].clear()
        
        logger.info(f"解像度変更: {resolution_str} ({new_resolution[0]}x{new_resolution[1]})")
        return jsonify({'status': 'success', 'resolution': resolution_str})
    
    except Exception as e:
        logger.error(f"解像度変更エラー: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@dashboard_bp.route('/test')
def test_api():
    """APIテストページ"""
    html = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>API Test</title>
</head>
<body>
    <h1>API Test Page</h1>
    <div id="result">Loading...</div>
    <script>
        console.log('Script started');
        async function testAPI() {
            try {
                console.log('Fetching /api/sensors...');
                const response = await fetch('/api/sensors');
                console.log('Response status:', response.status);
                const data = await response.json();
                console.log('Response data:', data);
                document.getElementById('result').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('result').innerHTML = 'Error: ' + error.message;
            }
        }
        testAPI();
    </script>
</body>
</html>"""
    return html

