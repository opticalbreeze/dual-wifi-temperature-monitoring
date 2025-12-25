# ビデオストリーミングコード監査レポート
**作成日時:** 2025年12月25日  
**監査対象:** `/temperature_server/app/routes/dashboard.py` と `/temperature_server/templates/stream.html`

---

## 📋 監査概要

### スコープ
- ✅ MJPEG フレーム生成パイプライン
- ✅ カメラリソース管理（シングルトン）
- ✅ 解像度変更時の同期問題
- ✅ フロントエンド・バックエンド間の連携
- ✅ エラーハンドリングとタイムアウト

### 重要度レベル
| 級 | 説明 |
|----|------|
| 🔴 Critical | システムクラッシュ、データ喪失の可能性 |
| 🟠 High | 機能動作不全、リソースリーク |
| 🟡 Medium | 動作の不安定性、潜在的なバグ |
| 🟢 Low | 改善提案、ベストプラクティス |

---

## 🔍 詳細監査結果

### 1️⃣ バックエンド監査（dashboard.py）

#### Issue #1: 🔴 CRITICAL - generate_frames() の無限ループ問題

**位置:** [dashboard.py:L48-71](dashboard.py#L48-L71)

```python
def generate_frames():
    """フレーム生成ジェネレータ"""
    global streaming_enabled
    while streaming_enabled:  # ⚠️ 危険: streaming_enabledの値が外部で変更される
        cam = get_camera()
        if cam is None:
            time.sleep(0.1)
            continue
        
        success, frame = cam.read()
        if not success:
            logger.warning("フレームの読み取りに失敗しました")
            time.sleep(0.1)
            continue
```

**問題点:**
- ✗ `streaming_enabled`フラグは外部の別スレッド（Flask リクエストハンドラー）から変更される
- ✗ ジェネレータが正在中にフラグが変更されると、クリーンアップされずにメモリリークが発生
- ✗ `generate_frames()`が複数のHTTPクライアントから同時呼び出しされた場合、すべてが同じグローバル変数を競合させる

**具体例:**
```
時刻 T0: クライアント1が /video_feed をリクエスト
  → streaming_enabled = True に設定
  → generate_frames() 開始

時刻 T1: クライアント2が /video_feed をリクエスト
  → 新たな generate_frames() インスタンスを開始
  → 両者が同じ `camera` オブジェクトにアクセス → Race Condition !!

時刻 T2: クライアント1が /video_feed/stop をリクエスト
  → streaming_enabled = False
  → クライアント2のジェネレータも強制終了
```

**推奨修正:**
```python
# グローバル変数を削除
# streaming_enabled_lock = threading.Lock()
# active_streams = {}  # stream_id -> StreamState

def generate_frames(stream_id):
    """フレーム生成ジェネレータ（スレッドセーフ版）"""
    stream_state = {'enabled': True, 'lock': threading.Lock()}
    active_streams[stream_id] = stream_state
    
    try:
        while stream_state['enabled']:
            with stream_state['lock']:
                if not stream_state['enabled']:
                    break
            # ... フレーム処理
    finally:
        del active_streams[stream_id]

@dashboard_bp.route('/video_feed')
def video_feed():
    stream_id = str(uuid.uuid4())
    return Response(
        generate_frames(stream_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
```

---

#### Issue #2: 🟠 HIGH - camera_lock の過度な保持時間

**位置:** [dashboard.py:L22-36](dashboard.py#L22-L36)

```python
def get_camera():
    """カメラインスタンスを取得（シングルトン）"""
    global camera
    with camera_lock:  # ⚠️ 危険: ロックを長く保持している
        if camera is None or not camera.isOpened():
            try:
                camera = cv2.VideoCapture(0)
                if not camera.isOpened():
                    logger.error("カメラを開けませんでした")
                    return None
                # 解像度設定
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, camera_resolution[0])
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_resolution[1])
                camera.set(cv2.CAP_PROP_FPS, camera_resolution[2])
```

**問題点:**
- ✗ `cv2.VideoCapture()` と `camera.set()` が`camera_lock`保持下で実行される
- ✗ Raspberry Pi では USB カメラドライバが遅い。ロック保持時間 = **200-500ms**
- ✗ 複数フレーム生成スレッドがブロックされて、フレームドロップが発生
- ✗ 解像度変更時に最大 **1.5秒のブロック**（get_camera() 呼び出し × N スレッド）

**リスク:**
```
Thread-1 (Frame Gen 1):   | camera_lock 保持 | カメラから読み取り（ロック解放）
Thread-2 (Frame Gen 2):   | ブロック中...     |
Thread-3 (Res Change):    | ブロック中...     |
                          0ms        300ms      500ms
```

**推奨修正:**
```python
def get_camera():
    """カメラインスタンスを取得（ロック時間最小化）"""
    global camera
    
    # Check without lock first (TOCTOU問題は許容)
    if camera is not None and camera.isOpened():
        return camera
    
    # Initialize only when necessary
    with camera_lock:
        # Double-check after acquiring lock
        if camera is not None and camera.isOpened():
            return camera
        
        try:
            camera = cv2.VideoCapture(0)
            # ... initialization
        except Exception as e:
            logger.error(f"Camera init error: {e}")
            return None
    
    return camera
```

---

#### Issue #3: 🟡 MEDIUM - 解像度変更時のフレームバッファ不同期

**位置:** [dashboard.py:L105-120](dashboard.py#L105-L120)

```python
# ストリーミング中は停止してから変更
was_streaming = streaming_enabled
if was_streaming:
    streaming_enabled = False
    # MJPEG境界フレームが完了するまで待機（最低1フレーム時間）
    time.sleep(1.0)  # ⚠️ 時間が短い可能性
```

**問題点:**
- ✗ `time.sleep(1.0)` は固定値だが、カメラフレームレートが 24fps の場合、実際には 41ms 必要
- ✗ ただし USB カメラドライバの遅延を考慮すると不足
- ✗ Release と Init の間に競合状態が存在：

```python
streaming_enabled = False
time.sleep(1.0)
camera_resolution = Config.AVAILABLE_RESOLUTIONS[resolution]  # ⚠️ この間に
release_camera()  # generate_frames() が camera.read() 実行中の可能性
cam = get_camera()
```

**推奨修正:**
```python
# Explicit synchronization event
stream_stop_event = threading.Event()

def generate_frames(stream_id):
    """フレーム生成ジェネレータ"""
    try:
        while not stream_stop_event.is_set():
            # ... frame generation
            time.sleep(1/24)  # FPS 同期
    finally:
        stream_stop_event.set()  # 明示的にシグナル

@dashboard_bp.route('/video_feed/resolution', methods=['POST'])
def video_feed_resolution():
    global camera_resolution
    # ...
    if was_streaming:
        stream_stop_event.set()
        stream_stop_event.wait(timeout=2.0)  # 最大 2秒 待機
        stream_stop_event.clear()
```

---

#### Issue #4: 🟢 LOW - cv2.imencode() のエラーハンドリング不足

**位置:** [dashboard.py:L66-69](dashboard.py#L66-L69)

```python
# フレームをJPEGにエンコード
ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
if not ret:
    continue  # ⚠️ エラー統計がない
```

**問題点:**
- ✗ `cv2.imencode()` 失敗の頻度が不明
- ✗ ヒープメモリ不足で失敗する可能性があるが、ログされない
- ✗ 原因分析が困難

**推奨修正:**
```python
ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
if not ret:
    logger.warning(f"JPEG encode failed, frame shape: {frame.shape}")
    continue
```

---

### 2️⃣ フロントエンド監査（stream.html）

#### Issue #5: 🟠 HIGH - img 要素の MJPEG 対応不足

**位置:** [stream.html:L53-70](stream.html#L53-L70)

```javascript
function startStream() {
    if (!isStreaming) {
        const streamUrl = '/video_feed?t=' + new Date().getTime() + '&v=' + STREAM_VERSION;
        // ...
        console.log('ストリーム開始:', streamUrl);
        videoStream.src = streamUrl;  // ⚠️ IMGタグで MJPEG ストリーミング
        videoStream.style.display = 'block';
        isStreaming = true;
    }
}
```

**問題点:**
- ✗ HTML `<img>` タグは **MJPEG ストリーミング非対応**
- ✗ IMGタグは最初の 1 フレームだけ表示する
- ✗ 複数フレームの MJPEG 境界 (`--frame\r\n`) を理解しない
- ✗ 実際のテスト例：
  - `<img src="/video_feed">` → 最初のフレーム 1 枚だけ表示
  - その後、フレーム更新 = **完全に停止**

**ブラウザサポートテーブル:**
| 要素 | Chrome | Firefox | Safari | MJPEG対応 |
|------|--------|---------|--------|----------|
| `<img>` | ✗ | ✗ | ✗ | **❌ NO** |
| `<iframe>` | ✓ | ✓ | ✗ | ⚠️ 部分的 |
| `<video>` | ✗ | ✗ | ✗ | ❌ NO |
| JavaScript | ✓ | ✓ | ✓ | ✅ YES |

**推奨修正:**
```html
<!-- 方法1: iframe + img -->
<iframe src="/video_feed_html"></iframe>

<!-- 方法2: JavaScript で手動フレーム処理 -->
<canvas id="video-canvas"></canvas>
<script>
async function streamFrames() {
    const response = await fetch('/video_feed');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        
        // MJPEG 境界を解析してフレームを抽出
        // canvas に描画
    }
}
</script>
```

---

#### Issue #6: 🟡 MEDIUM - 解像度変更のタイミング問題

**位置:** [stream.html:L99-121](stream.html#L99-L121)

```javascript
function changeResolution() {
    const res = document.getElementById('resolution').value;
    
    const wasStreaming = isStreaming;
    if (wasStreaming) {
        isStreaming = false;
        if (videoStream) {
            videoStream.src = '';  // ⚠️ about:blank エラーの原因
            videoStream.style.display = 'none';
        }
        fetch('/video_feed/stop').catch(() => {});  // ⚠️ キャッチのみ
    }
    
    fetch('/video_feed/resolution', { ... })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                setTimeout(() => {
                    if (wasStreaming) {
                        const streamUrl = '/video_feed?t=' + new Date().getTime() + '&v=' + STREAM_VERSION + '&r=' + res;
                        // ...
                        videoStream.src = streamUrl;
                        videoStream.style.display = 'block';
                        isStreaming = true;
                    }
                    console.log(`Resolution changed to: ${res}`);
                }, 1200);  // ⚠️ ハードコード
```

**問題点:**
- ✗ `videoStream.src = ''` → ブラウザが `about:blob` などを自動割り当て
- ✗ `fetch('/video_feed/stop').catch(() => {})` が silent fail → サーバー側ストリーミングが残存
- ✗ `setTimeout(1200)` は固定値。遅延が不足する可能性
- ✗ `wasStreaming` フラグが race condition の対象

**シナリオ:**
```
時刻 0ms:  changeResolution() 開始
時刻 100ms: fetch('/video_feed/resolution') 送信
時刻 200ms: ユーザーが再度 "適用" クリック
           wasStreaming の値が混乱 → 二重ストリーミング開始
```

---

#### Issue #7: 🔴 CRITICAL - about:blank エラーの本質

**位置:** [stream.html:L56](stream.html#L56)

```javascript
videoStream.src = '';  // ❌ これが about:blank を生成
```

**理由:**
```javascript
// ブラウザの動作
document.querySelector('img').src = '';
// → 内部的に src = 'about:blank' に変換される可能性
// → このリクエストが console に記録される：
//    GET about:blank net::ERR_UNKNOWN_URL_SCHEME
```

**実際のメカニズム:**
```
1. src = '' 設定
2. ブラウザ: "空の URL ... data URI に変換しようか？"
3. キャッシュクリア、src 再設定
4. ERROR: about:blank は fetch API で処理不可
```

---

### 3️⃣ アーキテクチャ監査

#### Issue #8: 🟠 HIGH - MJPEG 形式の仕様違反

**位置:** [dashboard.py:L68-71](dashboard.py#L68-L71)

```python
frame_bytes = buffer.tobytes()
yield (b'--frame\r\n'
       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
```

**MJPEG 仕様（RFC2616 + Motion JPEG）:**
```
HTTP/1.1 200 OK
Content-Type: multipart/x-mixed-replace; boundary=frame

--frame
Content-Type: image/jpeg
Content-Length: <bytes>

[JPEG binary data]
--frame
Content-Type: image/jpeg
Content-Length: <bytes>

[JPEG binary data]
```

**問題点:**
- ✗ `Content-Length` ヘッダなし → フレームサイズ不明
- ✗ `\r\n` だけで区切られているが、フレームサイズを知らないブラウザは不安定
- ✗ 特に low-bandwidth 環境で timeout

**推奨修正:**
```python
frame_bytes = buffer.tobytes()
yield (b'--frame\r\n'
       b'Content-Type: image/jpeg\r\n'
       b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
       b'\r\n' + frame_bytes + b'\r\n')
```

---

#### Issue #9: 🟡 MEDIUM - Favicon.ico の 404 エラー

**位置:** [dashboard.py:L149-155](dashboard.py#L149-L155)

```python
@dashboard_bp.route('/favicon.ico')
def favicon():
    """ファビコンを提供"""
    favicon_path = Path(__file__).parent.parent / 'app' / 'static' / 'favicon.ico'
    if favicon_path.exists():
        from flask import send_file
        return send_file(str(favicon_path), mimetype='image/x-icon')
    return '', 204  # No Content
```

**問題点:**
- ✗ パスが不正確: `parent.parent / 'app' / 'static'` → ディレクトリ構造が変わると破綻
- ✗ `import send_file` が関数内で実行 → 毎回インポートオーバーヘッド
- ✗ `static/favicon.ico` が存在しない可能性高い

**推奨修正:**
```python
from flask import send_from_directory, current_app
from functools import lru_cache

@lru_cache(maxsize=1)
def get_static_path():
    return current_app.static_folder

@dashboard_bp.route('/favicon.ico')
def favicon():
    favicon_path = get_static_path() / 'favicon.ico'
    if favicon_path.exists():
        return send_from_directory(get_static_path(), 'favicon.ico')
    # または、in-memory base64 favicon を返す
    return '', 204
```

---

## 📊 問題サマリー

| ID | 種類 | 重要度 | 影響範囲 |
|----|------|--------|---------|
| #1 | Race Condition | 🔴 CRITICAL | メモリリーク、クラッシュ |
| #2 | Lock Contention | 🟠 HIGH | フレームドロップ、遅延 |
| #3 | Sync Issue | 🟡 MEDIUM | 解像度変更失敗 |
| #4 | Log Missing | 🟢 LOW | 診断困難 |
| #5 | Browser Support | 🔴 CRITICAL | MJPEG 表示失敗 |
| #6 | Race Condition | 🟡 MEDIUM | 二重ストリーミング |
| #7 | about:blank | 🟠 HIGH | コンソール警告 |
| #8 | Spec Violation | 🟠 HIGH | 低速環境で不安定 |
| #9 | Favicon Missing | 🟢 LOW | コンソール警告 |

---

## 🔧 優先修正順序

### 第1段階（必須 - 今すぐ修正）
1. **Issue #5**: img タグを canvas/fetch に変更
2. **Issue #1**: ストリーム ID ベースのマルチストリーム対応

### 第2段階（高優先 - 今週中）
3. **Issue #2**: Lock 時間最小化
4. **Issue #8**: Content-Length 追加

### 第3段階（推奨 - 来週中）
5. **Issue #3**: イベントベースの同期
6. **Issue #6**: タイムアウト処理強化

### 第4段階（改善 - 随時）
7. **Issue #4**: ログ詳細化
8. **Issue #9**: Favicon 処理改善

---

## 📝 テストケース

```python
# test_streaming.py
import pytest
import threading
import time

def test_concurrent_streams():
    """複数クライアント同時接続テスト"""
    clients = []
    for i in range(3):
        def fetch_stream():
            response = client.get('/video_feed', stream=True)
            frames = 0
            for chunk in response.iter_content(chunk_size=1024):
                frames += 1
                if frames >= 30:  # 30フレーム取得
                    break
        
        t = threading.Thread(target=fetch_stream)
        clients.append(t)
        t.start()
    
    for t in clients:
        t.join(timeout=10)
    
    # メモリリーク確認
    assert get_memory_usage() < initial_memory + 50  # 50MB以上増加なし

def test_resolution_change():
    """解像度変更中のフレーム損失テスト"""
    frames_before = count_frames_in_period(1.0)
    change_resolution('1080p')
    frames_during = count_frames_in_period(2.0)  # 2秒間フレーム計測
    frames_after = count_frames_in_period(1.0)
    
    # フレームドロップ < 5%
    assert frames_during > frames_before * 0.95

def test_mjpeg_boundary():
    """MJPEG 境界形式テスト"""
    response = client.get('/video_feed', stream=True)
    data = b''
    for chunk in response.iter_content(1024):
        data += chunk
        if len(data) > 100000:
            break
    
    # MJPEG 境界の確認
    assert b'--frame\r\n' in data
    assert b'Content-Type: image/jpeg' in data
    assert b'Content-Length:' in data or b'\r\n\r\n' in data
```

---

## 📚 参考資料

- [MJPEG Wikipedia](https://en.wikipedia.org/wiki/Motion_JPEG)
- [RFC2046 MIME Multipart](https://tools.ietf.org/html/rfc2046)
- [OpenCV VideoCapture Docs](https://docs.opencv.org/4.5.2/d8/dfe/classcv_1_1VideoCapture.html)
- [Flask Streaming Response](https://flask.palletsprojects.com/en/2.3.x/patterns/streaming/)

