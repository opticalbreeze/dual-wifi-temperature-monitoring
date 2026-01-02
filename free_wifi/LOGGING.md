# ログ設定と確認方法

## 概要

Guest2-Repeaterプログラムは、GUIアプリケーションとして設計されていますが、systemdサービスとして実行することも可能です。このドキュメントでは、ログの設定方法と確認方法について説明します。

## ログ出力の仕組み

プログラムには2つのログ出力方法があります：

1. **GUIテキストボックスへの出力**（デフォルト）
   - プログラムのGUIウィンドウ内のテキストボックスにログを表示
   - ローカルでGUIが見える環境でのみ有効

2. **標準出力への出力**（systemdサービス用）
   - 標準出力（stdout）にログを出力
   - systemdのjournalに記録され、`journalctl`で確認可能
   - リモート操作時にもログを確認できる

## 設定方法

### config.py の設定

`config.py`ファイルでログ出力方法を制御します：

```python
# ログ設定
ENABLE_DEBUG_LOG = True          # デバッグログを出力する場合はTrue
ENABLE_STDOUT_LOG = True         # ログを標準出力に表示する場合はTrue（推奨）
MAX_LINES_LOG = 1000             # ログ表示行数最大値
```

### ENABLE_STDOUT_LOG の設定

- **`ENABLE_STDOUT_LOG = False`**（デフォルト）
  - ログはGUIのテキストボックスにのみ表示されます
  - systemdサービスとして実行する場合、ログが確認できません
  - リモート操作時にもログが確認できません

- **`ENABLE_STDOUT_LOG = True`**（推奨）
  - ログが標準出力に出力されます
  - systemdのjournalに記録され、`journalctl`で確認できます
  - リモート操作時にもログを確認できます
  - **systemdサービスとして運用する場合は、必ず`True`に設定してください**

## ログの確認方法

### systemdサービスとして実行している場合

#### 1. リアルタイムでログを確認

```bash
journalctl -u guest2-repeater.service -f
```

#### 2. 最近のログを確認

```bash
# 直近50行
journalctl -u guest2-repeater.service -n 50

# 過去1時間のログ
journalctl -u guest2-repeater.service --since "1 hour ago"

# 過去24時間のログ
journalctl -u guest2-repeater.service --since "24 hours ago"
```

#### 3. エラーログのみを確認

```bash
journalctl -u guest2-repeater.service -p err
```

#### 4. 特定のキーワードで検索

```bash
# "再接続"を含むログ
journalctl -u guest2-repeater.service | grep "再接続"

# "エラー"を含むログ
journalctl -u guest2-repeater.service | grep -i "error\|失敗"
```

### GUIアプリケーションとして実行している場合

GUIウィンドウ内のテキストボックスにログが表示されます。`ENABLE_STDOUT_LOG = False`でも問題ありません。

## トラブルシューティング

### 問題：ログが表示されない

**症状：**
- `journalctl -u guest2-repeater.service`でログが表示されない
- プログラムは動作しているが、ログが確認できない

**原因：**
- `config.py`の`ENABLE_STDOUT_LOG`が`False`になっている

**解決方法：**
1. `config.py`を編集して`ENABLE_STDOUT_LOG = True`に変更
2. 変更したファイルをRaspberry Piに送信
3. サービスを再起動：
   ```bash
   sudo systemctl restart guest2-repeater.service
   ```

### 問題：ログが多すぎる

**症状：**
- ログが大量に出力されて確認しにくい

**解決方法：**
1. `ENABLE_DEBUG_LOG = False`に設定してデバッグログを無効化
2. 特定の期間やキーワードでフィルタリングして確認

### 問題：GUIが見えない環境でログを確認したい

**症状：**
- リモート操作時やヘッドレス環境でGUIが見えない
- プログラムの動作状況を確認したい

**解決方法：**
1. `ENABLE_STDOUT_LOG = True`に設定
2. `journalctl`コマンドでログを確認

## 設定変更後の再起動

`config.py`を変更した後は、必ずサービスを再起動してください：

```bash
sudo systemctl restart guest2-repeater.service
```

変更が反映されているか確認：

```bash
sudo systemctl status guest2-repeater.service
journalctl -u guest2-repeater.service -n 20
```

## 推奨設定

systemdサービスとして運用する場合の推奨設定：

```python
# config.py
ENABLE_DEBUG_LOG = True          # デバッグ時はTrue、本番環境ではFalse
ENABLE_STDOUT_LOG = True         # systemdサービスとして運用する場合は必ずTrue
ENABLE_TRACEMALLOC_LOG = False   # メモリ使用量の追跡（通常はFalse）
MAX_LINES_LOG = 1000             # GUI表示用（ENABLE_STDOUT_LOG=Trueの場合は無視される）
```

## 関連ファイル

- `config.py` - ログ設定ファイル
- `main.py` - メインプログラム（ログ出力処理）
- `guest2-repeater.service` - systemdサービスファイル
- `start.sh` - 起動スクリプト

## 補足

### なぜ2つのログ出力方法があるのか

このプログラムは元々GUIアプリケーションとして設計されていました。そのため、ログはGUIのテキストボックスに表示する仕様になっていました。

しかし、systemdサービスとして運用する場合やリモート操作時には、GUIが見えないためログを確認できません。そこで、標準出力へのログ出力機能を追加し、systemdのjournalで確認できるようにしました。

### ログ出力の優先順位

`ENABLE_STDOUT_LOG = True`の場合：
- ログは標準出力に出力されます
- GUIのテキストボックスには出力されません（`return`で処理が終了するため）

`ENABLE_STDOUT_LOG = False`の場合：
- ログはGUIのテキストボックスにのみ出力されます
- 標準出力には何も出力されません

systemdサービスとして運用する場合は、必ず`ENABLE_STDOUT_LOG = True`に設定してください。

