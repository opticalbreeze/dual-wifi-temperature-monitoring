# 📱 ESP32 実装ガイド - 温度データ送信

**このガイドは、Raspberry Pi の AP に接続して、温度データを送信する ESP32 コードの実装方法を説明します**

---

## ✅ 必須コンポーネント

### ハードウェア

| パーツ | 型番/仕様 | 用途 |
|--------|----------|------|
| マイコン | ESP32 (任意モデル) | メイン制御 |
| 温度センサー | DS18B20 | 温度測定 |
| 抵抗 | 4.7kΩ | プルアップ |
| USB ケーブル | Micro USB | 電源 + 書き込み |

### ライブラリ

Arduino IDE で以下をインストール：

**ライブラリ管理から：**
- `OneWire` by Jim Studt, Paul Stoffregen
- `DallasTemperature` by Miles Burton
- `WiFi` (ESP32 組み込み)
- `HTTPClient` (ESP32 組み込み)

```
Arduino IDE → スケッチ → ライブラリをインクルード → ライブラリマネージャー
→ "OneWire" で検索 → インストール
→ "DallasTemperature" で検索 → インストール
```

---

## 🔌 ハードウェア接続

### DS18B20 配線図

```
      Raspberry Pi             ESP32
      (参考)                   (実装)

      +3.3V                    +3.3V
        │                        │
        ├─── 4.7kΩ抵抗 ─────────┼─── GPIO 4 (Data)
        │                        │
       VCC                      GND
       (Red)

      GND ───────────────────── GND
      (Black)

      Data ───────────────────── GPIO 4
      (Yellow)
```

### ジャンパーワイヤー接続

```
DS18B20 ピン配置（背面から見た場合、左から）
┌─────────┬─────────┬─────────┐
│   VCC   │  Data   │   GND   │
│  (+3.3V)│ (GPIO 4)│  (GND)  │
└─────────┴─────────┴─────────┘
```

---

## 📝 基本スケッチ（完全版）

```cpp
#include <OneWire.h>
#include <DallasTemperature.h>
#include <WiFi.h>
#include <HTTPClient.h>

// ===== ハードウェア定義 =====
#define ONE_WIRE_BUS 4  // GPIO 4 に接続
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// ===== WiFi 設定（重要：Raspberry Pi の AP に合わせる）=====
const char* SSID = "RaspberryPi_Temperature";      // SSID 名
const char* PASSWORD = "RaspberryPi2025";           // パスワード
const char* SERVER_IP = "192.168.4.1";              // Raspberry Pi の AP IP
const uint16_t SERVER_PORT = 5000;                   // Flask ポート

// ===== デバイス ID（複数の ESP32 を区別するため）=====
const char* DEVICE_ID = "ESP32_01";                 // 任意の名前
const char* DEVICE_NAME = "Living Room";            // 場所を示す名前
const char* DEVICE_LOCATION = "温度センサー";      // 詳細位置

// ===== 送信間隔 =====
const unsigned long SEND_INTERVAL = 30000;  // 30秒ごとに送信（ミリ秒）
unsigned long lastSendTime = 0;

// ===== ステータス表示 =====
bool lastConnectStatus = false;
unsigned long lastStatusUpdate = 0;
const unsigned long STATUS_UPDATE_INTERVAL = 5000;  // 5秒ごとに更新

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n=== ESP32 温度センサー開始 ===");
  Serial.println("ファームウェアバージョン: 1.0");
  Serial.println("ハードウェア: ESP32 + DS18B20");
  
  // DS18B20 初期化
  sensors.begin();
  Serial.print("DS18B20 デバイス数: ");
  Serial.println(sensors.getDeviceCount());
  
  // WiFi 接続開始
  connectToWiFi();
}

void loop() {
  // WiFi 接続状態の定期的なチェック
  handleWiFiConnection();
  
  // ステータス表示
  updateStatus();
  
  // 温度データ送信
  if (shouldSendData()) {
    sendTemperatureData();
  }
  
  delay(100);  // CPU の負荷軽減
}

// ===== WiFi 接続処理 =====
void connectToWiFi() {
  Serial.println("\n--- WiFi 接続開始 ---");
  Serial.print("SSID: ");
  Serial.println(SSID);
  
  WiFi.mode(WIFI_STA);  // ステーションモード
  WiFi.begin(SSID, PASSWORD);
  
  unsigned long startTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startTime < 20000) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println();
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("✓ WiFi 接続成功！");
    Serial.print("SSID: ");
    Serial.println(WiFi.SSID());
    Serial.print("IP アドレス: ");
    Serial.println(WiFi.localIP());
    Serial.print("信号強度: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println("✗ WiFi 接続失敗");
    Serial.println("設定を確認してください:");
    Serial.print("  - SSID: ");
    Serial.println(SSID);
    Serial.print("  - PASSWORD: ");
    Serial.println(PASSWORD);
  }
}

// ===== WiFi 接続状態の定期チェック =====
void handleWiFiConnection() {
  static unsigned long lastReconnect = 0;
  
  if (WiFi.status() != WL_CONNECTED) {
    // 接続が切れた場合
    if (millis() - lastReconnect > 30000) {  // 30秒ごと
      Serial.println("✗ WiFi 切断 - 再接続を試みます");
      WiFi.disconnect();
      delay(1000);
      connectToWiFi();
      lastReconnect = millis();
    }
  }
}

// ===== 定期的なステータス表示 =====
void updateStatus() {
  unsigned long now = millis();
  
  if (now - lastStatusUpdate > STATUS_UPDATE_INTERVAL) {
    bool currentConnectStatus = (WiFi.status() == WL_CONNECTED);
    
    // 接続状態が変わった場合に表示
    if (currentConnectStatus != lastConnectStatus) {
      Serial.println("\n--- ステータス更新 ---");
      Serial.print("WiFi: ");
      Serial.println(currentConnectStatus ? "接続中 ✓" : "切断中 ✗");
      
      if (currentConnectStatus) {
        Serial.print("IP: ");
        Serial.println(WiFi.localIP());
      }
      
      Serial.print("信号強度: ");
      Serial.print(WiFi.RSSI());
      Serial.println(" dBm");
      Serial.println("---");
      
      lastConnectStatus = currentConnectStatus;
    }
    
    lastStatusUpdate = now;
  }
}

// ===== 送信タイミングの判定 =====
bool shouldSendData() {
  unsigned long now = millis();
  return (now - lastSendTime > SEND_INTERVAL);
}

// ===== 温度データ読み取り =====
float readTemperature() {
  sensors.requestTemperatures();  // 計測開始
  float temp = sensors.getTempCByIndex(0);
  
  // エラーチェック
  if (temp == DEVICE_DISCONNECTED_C) {
    Serial.println("✗ DS18B20 エラー: センサーが見つかりません");
    return -999.0;
  }
  
  return temp;
}

// ===== サーバーへのデータ送信 =====
void sendTemperatureData() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("✗ WiFi に接続していません");
    return;
  }
  
  // 温度を読み取り
  float temperature = readTemperature();
  
  if (temperature == -999.0) {
    return;  // 読み取りエラー
  }
  
  // HTTP クライアント初期化
  HTTPClient http;
  
  // リクエスト URL を作成
  String url = "http://" + String(SERVER_IP) + ":" + String(SERVER_PORT) + "/api/temperature";
  
  Serial.print("\n--- データ送信開始 ---");
  Serial.print("URL: ");
  Serial.println(url);
  
  // HTTP POST リクエスト
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // JSON ペイロード作成
  String payload = createJsonPayload(temperature);
  Serial.print("ペイロード: ");
  Serial.println(payload);
  
  // POST 送信
  int httpResponseCode = http.POST(payload);
  
  // レスポンス処理
  Serial.print("レスポンスコード: ");
  Serial.println(httpResponseCode);
  
  if (httpResponseCode == 201 || httpResponseCode == 200) {
    Serial.println("✓ 送信成功");
    String response = http.getString();
    Serial.print("サーバー応答: ");
    Serial.println(response);
    lastSendTime = millis();
  } else if (httpResponseCode == -1) {
    Serial.println("✗ 接続エラー (ホストに接続できません)");
    Serial.print("ホスト: ");
    Serial.print(SERVER_IP);
    Serial.print(":");
    Serial.println(SERVER_PORT);
  } else {
    Serial.println("✗ サーバーエラー");
    String response = http.getString();
    Serial.println(response);
  }
  
  http.end();
  Serial.println("---");
}

// ===== JSON ペイロード生成 =====
String createJsonPayload(float temperature) {
  String json = "{";
  json += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  json += "\"device_name\":\"" + String(DEVICE_NAME) + "\",";
  json += "\"location\":\"" + String(DEVICE_LOCATION) + "\",";
  json += "\"temperature\":" + String(temperature, 2) + ",";
  json += "\"timestamp\":\"" + getFormattedTimestamp() + "\"";
  json += "}";
  
  return json;
}

// ===== タイムスタンプ生成（簡易版）=====
String getFormattedTimestamp() {
  // 簡易版：実装が必要な場合は、NTP で時刻を同期するか、
  // サーバー側でタイムスタンプを生成することを推奨
  return "auto";  // サーバーで自動生成されます
}

// ===== シリアル出力の詳細情報（デバッグ用）=====
void printDebugInfo() {
  Serial.println("\n=== デバッグ情報 ===");
  Serial.print("WiFi SSID: ");
  Serial.println(WiFi.SSID());
  Serial.print("WiFi 強度: ");
  Serial.println(WiFi.RSSI());
  Serial.print("デバイス ID: ");
  Serial.println(DEVICE_ID);
  Serial.print("サーバーアドレス: ");
  Serial.print(SERVER_IP);
  Serial.print(":");
  Serial.println(SERVER_PORT);
  Serial.print("最終送信: ");
  Serial.print((millis() - lastSendTime) / 1000);
  Serial.println(" 秒前");
  Serial.println("=================");
}
```

---

## 🔧 設定項目の説明

### WiFi 設定

```cpp
const char* SSID = "RaspberryPi_Temperature";    // Raspberry Pi の AP SSID
const char* PASSWORD = "RaspberryPi2025";         // 設定したパスワード
const char* SERVER_IP = "192.168.4.1";            // AP のIP アドレス
const uint16_t SERVER_PORT = 5000;                // Flask のポート
```

**注意**：
- SSID が一致しないと接続できません
- パスワードが一致しないと接続できません
- SERVER_IP は Raspberry Pi の wlan1 のIP である必要があります

### デバイス設定

```cpp
const char* DEVICE_ID = "ESP32_01";          // 一意の ID
const char* DEVICE_NAME = "Living Room";     // 人が読める名前
const char* DEVICE_LOCATION = "温度センサー";  // 詳細な場所
```

複数の ESP32 を使用する場合は、各デバイスで DEVICE_ID を変更してください。

例：
```cpp
// ESP32-1
const char* DEVICE_ID = "ESP32_01";
const char* DEVICE_NAME = "リビング";

// ESP32-2
const char* DEVICE_ID = "ESP32_02";
const char* DEVICE_NAME = "キッチン";

// ESP32-3
const char* DEVICE_ID = "ESP32_03";
const char* DEVICE_NAME = "寝室";
```

### 送信間隔

```cpp
const unsigned long SEND_INTERVAL = 30000;  // ミリ秒（30秒 = 30000）
```

変更例：
- 10秒ごと：`10000`
- 60秒ごと：`60000`
- 5分ごと：`300000`

---

## ⚙️ トラブルシューティング

### Issue 1: コンパイルエラー

#### エラー: `'OneWire' does not name a type`

```
原因：OneWire ライブラリがインストールされていない

解決：
1. Arduino IDE を開く
2. スケッチ → ライブラリをインクルード → ライブラリマネージャー
3. "OneWire" で検索
4. Jim Studt, Paul Stoffregen のバージョンをインストール
5. 同様に "DallasTemperature" もインストール
```

### Issue 2: ESP32 が WiFi に接続できない

#### シリアル出力：
```
--- WiFi 接続開始 ---
SSID: RaspberryPi_Temperature
.....
✗ WiFi 接続失敗
```

#### 診断

```cpp
// シリアルモニターで詳細を確認
Serial.print("WiFi Status: ");
Serial.println(WiFi.status());
// 0: WL_IDLE_STATUS (接続待機中)
// 1: WL_NO_SSID_AVAIL (SSID が見つからない)
// 2: WL_SCAN_COMPLETED (スキャン完了)
// 3: WL_CONNECTED (接続成功)
// 4: WL_CONNECT_FAILED (接続失敗)
// 5: WL_CONNECTION_LOST (接続ロスト)
// 6: WL_WRONG_PASSWORD (パスワード間違い)
```

#### 解決方法

**SSID または パスワード間違い**
```cpp
Serial.print("SSID: ");
Serial.println(SSID);
Serial.print("PASSWORD: ");
Serial.println(PASSWORD);

// Raspberry Pi で確認
// sudo cat /etc/hostapd/hostapd.conf | grep "ssid\|wpa_passphrase"
```

**Raspberry Pi の AP が起動していない**
```cpp
// Raspberry Pi で確認
sudo systemctl status hostapd
sudo iw dev wlan1 link

// スキャンして SSID が見える確認
sudo iwlist wlan0 scan | grep -i "RaspberryPi_Temperature"
```

### Issue 3: データが送信されない（WiFi は接続している）

#### シリアル出力：
```
✓ WiFi 接続成功！
IP アドレス: 192.168.4.185
...
✗ 接続エラー (ホストに接続できません)
```

#### 診断

```bash
# Raspberry Pi から確認
ping 192.168.4.185  # ESP32 へ ping

# Flask が起動しているか確認
sudo systemctl status temperature-server

# Flask がリッスンしているか確認
sudo netstat -tlnp | grep 5000
```

#### 解決方法

**Flask が起動していない**
```bash
sudo systemctl restart temperature-server
sudo systemctl status temperature-server
```

**SERVER_IP が間違っている**
```cpp
// Raspberry Pi で確認
ip addr show wlan1 | grep inet

// コード内で修正
const char* SERVER_IP = "192.168.4.1";  // 確認した IP を入力
```

### Issue 4: DS18B20 が読み取れない

#### シリアル出力：
```
DS18B20 デバイス数: 0
✗ DS18B20 エラー: センサーが見つかりません
```

#### 診断

```cpp
// ピン番号を確認
#define ONE_WIRE_BUS 4  // GPIO 4 に接続しているか？

// シリアルモニターで確認
sensors.getDeviceCount() == 0  // 0 の場合は接続なし
```

#### 解決方法

**接続確認**
```
GPIO 4 (Data) ← 黄色ワイヤー
+3.3V ← 赤ワイヤー（抵抗経由）
GND ← 黒ワイヤー
```

**ピン番号の変更**
```cpp
// 別の GPIO を使用する場合
#define ONE_WIRE_BUS 5  // GPIO 5 に変更
// または
#define ONE_WIRE_BUS 18
```

---

## 📊 API リクエスト形式

### POST /api/temperature

**期待される JSON:**
```json
{
  "device_id": "ESP32_01",
  "device_name": "Living Room",
  "location": "温度センサー",
  "temperature": 23.50,
  "timestamp": "auto"
}
```

**成功時のレスポンス:**
```json
{
  "status": "success",
  "message": "Temperature data recorded",
  "timestamp": "2025-12-24T06:07:06",
  "temperature": 23.50
}
```

**エラーレスポンス:**
```json
{
  "status": "error",
  "message": "Invalid JSON or missing fields"
}
```

---

## 📈 パフォーマンス最適化

### 消費電力削減

```cpp
// スリープモードの使用（30秒ごとに送信する場合）
#define SLEEP_DURATION 25000  // 25秒スリープ

void sleepAndWakeup() {
  Serial.println("スリープに入ります...");
  esp_sleep_enable_timer_wakeup(SLEEP_DURATION * 1000);
  esp_light_sleep_start();
  Serial.println("起動しました");
}

// loop() 内で使用
if (shouldSendData()) {
  sendTemperatureData();
  sleepAndWakeup();  // 送信後にスリープ
}
```

### メモリ使用量削減

```cpp
// Flash メモリの文字列を使用
const char* SSID = "RaspberryPi_Temperature";  // RAM に格納される

// 改善版（PROGMEM を使用）
const char SSID[] PROGMEM = "RaspberryPi_Temperature";
```

---

## 🔐 セキュリティに関する注意

⚠️ **本番環境での推奨事項：**

1. **パスワード管理**
   ```cpp
   // 本番環境では、パスワードをコードに埋め込まない
   // 代わりに EEPROM に保存するか、設定サーバーから取得する
   ```

2. **HTTPS の使用**
   ```cpp
   // 現在は HTTP ですが、本番では HTTPS を使用してください
   const char* SERVER_IP = "https://...";
   ```

3. **認証トークン**
   ```cpp
   http.addHeader("Authorization", "Bearer YOUR_TOKEN");
   ```

---

## 📚 参考リンク

- [Arduino IDE インストール](https://www.arduino.cc/en/software)
- [OneWire ライブラリ](https://github.com/PaulStoffregen/OneWire)
- [DallasTemperature ライブラリ](https://github.com/milesburton/Arduino-Temperature-Control-Library)
- [ESP32 技術仕様](https://www.espressif.com/en/products/socs/esp32)
- [DS18B20 データシート](https://datasheets.maximintegrated.com/en/ds/DS18B20.pdf)

---

**最後に更新**: 2025年12月24日
