"""
temperature_server/app/routes/dashboard.py
ダッシュボードルート
"""

from flask import Blueprint, render_template, Response
from logger import setup_logger
import sys
from pathlib import Path

# パス設定
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger = setup_logger(__name__)
dashboard_bp = Blueprint('dashboard', __name__)

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
        
        # カメラ設定
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        def generate_frames():
            """フレームジェネレータ"""
            frame_count = 0
            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("フレーム読み込み失敗")
                        break
                    
                    # JPEGエンコード
                    ret, buffer = cv2.imencode('.jpg', frame)
                    frame_bytes = buffer.tobytes()
                    
                    # MJPEGストリーム形式で返す
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n'
                           b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
                           b'\r\n' + frame_bytes + b'\r\n')
                    
                    frame_count += 1
                    if frame_count % 100 == 0:
                        logger.debug(f"ビデオフィード: {frame_count}フレーム送信")
            except Exception as e:
                logger.error(f"ビデオフィード生成エラー: {e}")
            finally:
                cap.release()
        
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

