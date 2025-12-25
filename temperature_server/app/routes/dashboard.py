from flask import Blueprint, render_template, Response, request, jsonify
from logger import setup_logger
import cv2
from config import Config
import threading
import time
import os
from pathlib import Path

logger = setup_logger(__name__)
dashboard_bp = Blueprint('dashboard', __name__)

# グローバル変数
camera = None
camera_lock = threading.Lock()
camera_resolution = Config.AVAILABLE_RESOLUTIONS[Config.DEFAULT_RESOLUTION]
streaming_enabled = False

def get_camera():
    """カメラインスタンスを取得（シングルトン）"""
    global camera
    with camera_lock:
        if camera is None or not camera.isOpened():
            try:
                import os
                # /dev/video* ファイルを直接確認
                video_devices = []
                for i in range(0, 32):
                    dev_path = f'/dev/video{i}'
                    if os.path.exists(dev_path):
                        video_devices.append(i)
                
                logger.info(f"検出されたビデオデバイス: {[f'/dev/video{i}' for i in video_devices]}")
                
                # カメラデバイスを検索（実際に存在するデバイスのみ試す）
                camera_index = None
                for i in video_devices:
                    try:
                        test_camera = cv2.VideoCapture(i)
                        if test_camera.isOpened():
                            # 実際にフレームを読み取れるか確認
                            ret, frame = test_camera.read()
                            test_camera.release()
                            if ret and frame is not None:
                                camera_index = i
                                logger.info(f"カメラデバイス /dev/video{i} を検出しました (解像度: {frame.shape[1]}x{frame.shape[0]})")
                                break
                    except Exception as e:
                        logger.debug(f"デバイス /dev/video{i} のテスト中にエラー: {e}")
                        continue
                
                if camera_index is None:
                    logger.error("利用可能なカメラデバイスが見つかりませんでした")
                    return None
                
                camera = cv2.VideoCapture(camera_index)
                if not camera.isOpened():
                    logger.error(f"カメラ /dev/video{camera_index} を開けませんでした")
                    return None
                # 解像度設定
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, camera_resolution[0])
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_resolution[1])
                camera.set(cv2.CAP_PROP_FPS, camera_resolution[2])
                logger.info(f"カメラを初期化しました: {camera_resolution[0]}x{camera_resolution[1]}@{camera_resolution[2]}fps")
            except Exception as e:
                logger.error(f"カメラ初期化エラー: {e}")
                return None
        return camera

def release_camera():
    """カメラを解放"""
    global camera
    with camera_lock:
        if camera is not None:
            camera.release()
            camera = None
            logger.info("カメラを解放しました")

def generate_frames():
    """フレーム生成ジェネレータ"""
    global streaming_enabled
    while streaming_enabled:
        cam = get_camera()
        if cam is None:
            time.sleep(0.1)
            continue
        
        success, frame = cam.read()
        if not success:
            logger.warning("フレームの読み取りに失敗しました")
            time.sleep(0.1)
            continue
        
        # フレームをJPEGにエンコード
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            logger.warning(f"JPEG encode failed, frame shape: {frame.shape}")
            continue
        
        frame_bytes = buffer.tobytes()
        # MJPEG仕様に準拠: Content-Lengthを追加
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
               b'\r\n' + frame_bytes + b'\r\n')

@dashboard_bp.route('/')
def index():
    """ダッシュボード"""
    return render_template('dashboard.html')

@dashboard_bp.route('/stream')
def stream():
    """ビデオストリーミング"""
    return render_template('stream.html')

@dashboard_bp.route('/video_feed_html')
def video_feed_html():
    """MJPEGストリーミング用HTMLページ（iframe用）"""
    return render_template('video_feed_frame.html')

@dashboard_bp.route('/video_feed')
def video_feed():
    """MJPEGストリーミングエンドポイント"""
    global streaming_enabled
    streaming_enabled = True
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@dashboard_bp.route('/video_feed/stop')
def video_feed_stop():
    """ストリーミング停止"""
    global streaming_enabled
    streaming_enabled = False
    release_camera()
    return jsonify({'status': 'stopped'}), 200

@dashboard_bp.route('/video_feed/resolution', methods=['POST'])
def video_feed_resolution():
    """解像度変更 - フレームバッファ同期を考慮"""
    global camera_resolution, streaming_enabled
    try:
        if not request.is_json:
            return jsonify({'status': 'error', 'message': 'JSON形式で送信してください'}), 400
        
        resolution = request.json.get('resolution', Config.DEFAULT_RESOLUTION)
        if resolution not in Config.AVAILABLE_RESOLUTIONS:
            return jsonify({'status': 'error', 'message': '無効な解像度'}), 400
        
        # ストリーミング中は停止してから変更
        was_streaming = streaming_enabled
        if was_streaming:
            streaming_enabled = False
            # MJPEG境界フレームが完了するまで待機（最低1フレーム時間）
            time.sleep(1.0)  # フレーム生成が完全に停止するまで待機
        
        camera_resolution = Config.AVAILABLE_RESOLUTIONS[resolution]
        release_camera()  # カメラをリセット
        
        # 新しい解像度でカメラを再初期化
        cam = get_camera()
        if cam is None:
            return jsonify({'status': 'error', 'message': 'カメラの再初期化に失敗しました'}), 500
        
        # CAP_PROP設定の遅延を考慮して、数フレーム読み捨てる
        for _ in range(3):
            cam.read()
        time.sleep(0.1)  # フレームバッファが新しい解像度で安定するまで待機
        
        # ストリーミングを再開（フロントエンドで新しいストリームを開始するためFalseのまま）
        # フロントエンド側で新しいストリームを開始させる
        
        logger.info(f"解像度を変更しました: {resolution} ({camera_resolution[0]}x{camera_resolution[1]})")
        return jsonify({
            'status': 'success', 
            'resolution': resolution,
            'streaming': False  # フロントエンドで再開させる
        }), 200
    except Exception as e:
        logger.error(f"解像度変更エラー: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@dashboard_bp.route('/favicon.ico')
def favicon():
    """ファビコンを提供"""
    # favicon.icoが存在しない場合は204を返す
    favicon_path = Path(__file__).parent.parent / 'app' / 'static' / 'favicon.ico'
    if favicon_path.exists():
        from flask import send_file
        return send_file(str(favicon_path), mimetype='image/x-icon')
    return '', 204  # No Content

@dashboard_bp.route('/management')
def management():
    """管理画面"""
    return render_template('management.html')
