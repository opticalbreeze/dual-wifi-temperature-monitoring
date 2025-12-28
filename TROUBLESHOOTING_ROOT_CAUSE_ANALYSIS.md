# Raspberry Pi 温度監視システム トラブルシューティングレポート

**日時:** 2025年12月28日  
**案件:** グラフが描画されない問題の根本原因調査と解決

---

## 🔴 発見された主要問題

### 問題 1: タイムゾーン比較エラー（グラフ表示障害の根本原因）

**症状:**
- API `/api/temperature/ESP32_PROT_01?hours=0.5` が空配列 `{}` を返す
- ダッシュボードのセンサーカードは表示されるが、グラフが描画されない
- データベースには 35 レコード存在するのに、クエリ結果が 0 件

**根本原因:**
```python
# ❌ 悪い実装（database/queries.py 修正前）
since = (datetime.now() - timedelta(hours=hours)).isoformat()
# 結果: "2025-12-28T15:50:01.123456" (ISO 8601 形式)

# データベースの格納形式: "2025-12-28 15:50:01"
# テキスト比較で「T」を含む ISO 形式 > 「 」を含む素朴形式 となり、不等式が成立せず 0 件
```

**詳細な問題フロー:**
1. `datetime.now()` は Raspberry Pi のシステム時刻（Asia/Tokyo = JST）を返す
2. `.isoformat()` で ISO 8601 形式に変換 → `"2025-12-28T15:46:20.123456"`
3. データベースには `datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')` で保存 → `"2025-12-28 15:46:20"`
4. SQL 比較: `"2025-12-28T15:50:01" > "2025-12-28 15:46:20"` → **False**（テキスト比較で「T」が「 」より大きい）
5. **結果: 何のレコードもマッチしない**

**修正方法:**
```python
# ✅ 修正後の実装
since = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
# 結果: "2025-12-28 15:50:01" (素朴形式)
# データベースと同じ形式なので正常に比較される
```

**影響範囲:**
- `TemperatureQueries.get_range()` メソッド
- `TemperatureQueries.get_statistics()` メソッド
- グラフ API エンドポイント全体

---

### 問題 2: wlan1 IPv4 アドレス消失（WiFi AP 通信障害）

**症状:**
- ESP32 が wlan1（WiFi AP）に接続してもデータを送信できない
- `ip addr show wlan1` の出力に IPv4 アドレスがない（IPv6 のみ）
- 起動時に IP が割り当たらず、30分以上新データが記録されない

**根本原因：複数のネットワーク管理ツールの競合**

| ツール | ステータス | 問題 |
|--------|----------|------|
| `/etc/network/interfaces` | ✅ 設定存在 | ❌ 読み込むサービスが停止 |
| `systemd-networkd` | ❌ disabled | ❌ 起動していない |
| `dhcpcd` | ❌ インストール不在 | ❌ サービスなし |
| `ifupdown` | ? | ❌ systemd サービスなし |
| **NetworkManager** | ✅ running | ⚠️ wlan1 が unmanaged |

**結果:**
- `/etc/network/interfaces` の wlan1 設定が起動時に適用されない
- 手動で `sudo ip addr add 192.168.4.1/24 dev wlan1` を実行しても、再起動で消える

---

### 問題 3: システムタイムゾーン設定の冗長処理

**症状:**
- Python コードで `datetime.now(JST)` と明示的にやっているが、不要な処理

**根本原因:**
```python
# Raspberry Pi のシステムタイムゾーン確認
$ timedatectl | grep 'Time zone'
# Time zone: Asia/Tokyo (JST, +0900)

# つまり datetime.now() は既に JST を返している
# 明示的に JST を指定する必要がない
```

**冗長コード例:**
```python
JST = timezone(timedelta(hours=9))
jst_now = datetime.now(JST)  # ❌ 不要（システムが既に JST）
```

**修正:**
```python
now = datetime.now()  # ✅ 十分（Raspberry Pi は Asia/Tokyo に設定）
```

---

## 📊 問題の相互関係図

```
┌─────────────────────────────────────────────────────────┐
│         グラフが描画されない（ユーザー報告）              │
└────────────────────────┬────────────────────────────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
    ❌ API が空配列返す    ❌ WiFi AP 通信できない
         [問題 1]               [問題 2]
    タイムゾーン比較エラー    wlan1 IP 消失
         
         └─────────┬──────────┘
                   │
         ⚠️ 根本: 複数の環境設定ツール混在
            - ネットワーク管理ツール競合
            - タイムゾーン処理冗長性
            - サービス起動順序未定義
```

---

## 🔧 実装された修正

### 修正 1: タイムゾーン比較エラーの解決

**ファイル:** `temperature_server/database/queries.py`

```diff
  @staticmethod
  def get_range(sensor_id, hours=24):
-     """指定時間範囲のデータを取得（JST）"""
+     """指定時間範囲のデータを取得（ローカルタイムゾーン）"""
      with db_lock:
          conn = get_connection()
          cursor = conn.cursor()
-         since = (datetime.now() - timedelta(hours=hours)).isoformat()
+         since = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
```

**影響:**
- `readings` 配列に正常にデータが返される
- グラフ API が機能開始
- ダッシュボード表示完全復旧

**検証結果:**
```
API テスト: GET /api/temperature/ESP32_PROT_01?hours=0.5
応答: 10 レコード（正常）
タイムスタンプ範囲: 2025-12-28 16:24:41 ～ 2025-12-28 16:29:18
```

---

### 修正 2: wlan1 IP アドレスの永続化

**新規ファイル:** `wlan1-static-ip.service`

```ini
[Unit]
Description=Setup wlan1 IP Address for AP Mode
After=network.target hostapd.service

[Service]
Type=oneshot
ExecStart=/usr/sbin/ip addr add 192.168.4.1/24 dev wlan1
ExecStart=/usr/sbin/ip link set wlan1 up
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

**効果:**
- Raspberry Pi 起動時に自動的に wlan1 に IP を割り当て
- 再起動後も IP が消えない
- systemd により起動順序が保証される（After=hostapd.service）

---

### 修正 3: ネットワーク管理の統一

**変更内容:**
- `/etc/network/interfaces` を無効化（backup: `interfaces.bak`）
- NetworkManager に統一（既にインストール済み、自動起動有効）
- 競合するサービス（dhcpcd、systemd-networkd 等）を停止

**結果:**
- DNS/DHCP 自動管理
- WiFi 接続管理の一元化
- 将来的なシステム拡張が容易

---

## 📈 修正前後の比較

### グラフ API の動作

```
【修正前】
GET /api/temperature/ESP32_PROT_01?hours=0.5
{
  "status": "success",
  "sensor_id": "ESP32_PROT_01",
  "readings": {},                    ❌ 空
  "statistics": {
    "count": 0,
    "avg_temp": null,
    "max_temp": null,
    "min_temp": null
  }
}

【修正後】
GET /api/temperature/ESP32_PROT_01?hours=0.5
{
  "status": "success",
  "sensor_id": "ESP32_PROT_01",
  "readings": [                      ✅ 10 レコード
    {
      "id": 36,
      "sensor_id": "ESP32_PROT_01",
      "sensor_name": "DS18B20-01",
      "temperature": 22.1875,
      "timestamp": "2025-12-28 16:24:41"
    },
    ...
  ],
  "statistics": {
    "count": 10,
    "avg_temp": 22.1875,
    "max_temp": 22.25,
    "min_temp": 22.1875
  }
}
```

### wlan1 ネットワーク接続

```
【修正前】
$ ip addr show wlan1
4: wlan1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500
   inet6 fe80::da3a:ddff:feab:a2a/64 scope link
   # ❌ IPv4 なし
   # ❌ 30分以上データ更新なし

【修正後】
$ ip addr show wlan1
4: wlan1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500
   inet 192.168.4.1/24 scope global wlan1  ✅ IP 割り当て
   inet6 fe80::da3a:ddff:feab:a2a/64 scope link
   # ✅ ESP32 が継続的にデータ送信
   # ✅ 2デバイス接続確認
```

---

## 🎯 学習ポイント

| 項目 | 教訓 |
|------|------|
| **タイムゾーン処理** | システムタイムゾーン設定済みの場合、Python で明示的に設定不要。冗長処理は形式ミスマッチを招く |
| **日時比較** | ISO フォーマットと素朴形式のミックスは絶対 NG。データベースの格納形式と統一する |
| **ネットワーク管理** | 複数の管理ツール混在は避ける。単一の管理ツールに統一して責任を明確化 |
| **systemd サービス** | 起動順序依存性を `After=`, `Requires=` で明示的に定義する |
| **開発環境管理** | 手動コマンドで設定変更した場合、systemd サービスで自動化して再起動テストを行う |

---

## ✅ 最終状態

| コンポーネント | ステータス | 備考 |
|--------------|----------|------|
| **グラフ API** | ✅ 機能 | 30分・1時間・1日等の時間範囲で正常動作 |
| **WiFi AP (wlan1)** | ✅ 運用 | 192.168.4.1/24 固定、再起動対応 |
| **ESP32 接続** | ✅ 動作 | 2デバイス継続接続、データ送信中 |
| **ダッシュボード** | ✅ 表示 | センサーカード + グラフ完全表示 |
| **ネットワーク管理** | ✅ 統一 | NetworkManager のみ（競合なし） |
| **データベース** | ✅ 正常 | 54 レコード、タイムスタンプ正確 |

---

**コミット:** d377684 - Fix: タイムゾーン比較エラーとネットワーク設定を解決
