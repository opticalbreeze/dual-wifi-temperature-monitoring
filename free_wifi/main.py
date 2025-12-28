"""
Guest2-Repeater - 院内フリーWi-Fi中継器
Raspbian（ラズビアン）専用メインプログラム

このプログラムはRaspbian（Raspberry Pi OS）専用です。
他のOSでは動作しません。

このプログラムの主な機能：
1. インターネット接続を定期的に監視（5分ごと）
2. 接続が切れた場合、自動的に再接続処理を実行
3. キャプティブポータル（認証ページ）を自動処理
4. GUIで状態を表示

初心者向けガイド：
- config.py で動作設定を変更できます
- start.sh で起動します
- 再接続ボタンで手動再接続できます
"""

# === 必要なライブラリのインポート ===

import time              # 時間処理（sleep等）
import threading        # 並列処理（バックグラウンドで監視）
import requests         # HTTP通信（接続確認用）
import subprocess       # システムコマンド実行（sudo rfkill等）
import gc               # メモリ管理（ガベージコレクション）
import tracemalloc      # メモリ使用量の追跡（デバッグ用）
import tkinter as tk    # GUIライブラリ（ウィンドウ表示用）
from datetime import datetime
from tkinter import Text, font, messagebox

# Selenium - ブラウザ自動操作用ライブラリ
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# プロジェクト内のモジュール
import config        # 設定ファイル（config.py）
import lib_utils    # ユーティリティ関数（lib_utils.py）


# === メインクラスの定義 ===
class Application(tk.Frame):

    def __init__(self, master):
        """
        初期化処理
        
        このメソッドは起動時に1回だけ実行されます。
        設定ファイルから値を読み込み、GUIを準備し、WebDriverを起動します。
        
        Args:
            master: Tkinterのルートウィンドウ
        """
        super().__init__(master)
        
        # === 設定ファイル（config.py）から値を取得 ===
        self.ENABLE_DEBUG_LOG = config.ENABLE_DEBUG_LOG          # デバッグログの有効/無効
        self.ENABLE_TRACEMALLOC_LOG = config.ENABLE_TRACEMALLOC_LOG  # メモリ使用量ログ
        self.ENABLE_STDOUT_LOG = config.ENABLE_STDOUT_LOG        # 標準出力にログ出力
        self.MAX_LINES_LOG = config.MAX_LINES_LOG                # ログ表示最大行数
        self.INTERVAL_ALIVE = config.INTERVAL_ALIVE               # 接続確認周期（秒）
        self.INTERVAL_TRACEMALLOC = config.INTERVAL_TRACEMALLOC   # メモリ表示周期
        self.INTERVAL_WEBDRIVER = config.INTERVAL_WEBDRIVER       # WebDriver更新周期
        self.TEST_PAGE_URL = config.TEST_PAGE_URL                 # テストページのURL
        self.TEST_PAGE_CURRENT_URL = config.TEST_PAGE_CURRENT_URL # 認証後のURL
        
        # === WebDriver（ブラウザ自動操作用）のパスを取得 ===
        self.PATH_WEBDRIVER = config.get_webdriver_path()

        # === 状態管理用の変数 ===
        self.is_alive = False                # インターネット接続状態（True=接続中）
        self.time_last_alive = 0            # 最後に接続確認した時刻
        self.time_last_tracemalloc = 0       # 最後にメモリ表示した時刻
        self.time_last_webdriver = 0        # 最後にWebDriver更新した時刻
        self.is_initializing = True          # 初期化中フラグ
        self.is_webdriver_updating = False  # WebDriver更新中フラグ
        self.is_reconnecting = False         # 再接続処理中フラグ
        self.is_dialog = False              # ダイアログ表示中フラグ
        self.cnt_auto_recconet_error = 0    # 自動再接続のエラー回数（最大3回）
        
        # === メモリ使用量の追跡を開始（デバッグ用）===
        if self.ENABLE_TRACEMALLOC_LOG:
            tracemalloc.start()
        
        # === GUIウィンドウの基本設定 ===
        self.pack(fill=tk.BOTH)  # ウィンドウ全体に配置

        master.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")  # ウィンドウサイズ
        master.title(config.WINDOW_TITLE)  # ウィンドウタイトル
        
        # === フォント設定（フォールバック機能付き）===
        # Raspbian（ラズビアン）で利用可能なフォントを自動検出
        self.MONO_FONT_FAMILY = self._get_available_font(config.MONO_FONT_FAMILY)
        
        # フォント変更があった場合は後でログ出力
        if self.MONO_FONT_FAMILY != config.MONO_FONT_FAMILY:
            self._deferred_font_log = f"フォント '{config.MONO_FONT_FAMILY}' が見つかりません。'{self.MONO_FONT_FAMILY}' を使用します。"
        else:
            self._deferred_font_log = None
            
        # 3つのサイズのフォントを準備
        self.FONT_L = tk.font.Font(family=self.MONO_FONT_FAMILY, size=14, weight="normal")  # 大
        self.FONT_M = tk.font.Font(family=self.MONO_FONT_FAMILY, size=12, weight="normal")  # 中
        self.FONT_S = tk.font.Font(family=self.MONO_FONT_FAMILY, size=9, weight="normal")  # 小
        
        # === GUI のボタン・ラベル等を準備 ===
        self._create_widgets()
        
        # === WebDriver（ブラウザ自動操作用）を準備 ===
        # この処理は数分かかることがあります（Chromium起動のため）
        self.logging("Webドライバーを準備しています...(この処理は数分かかることがあります)")
        try:
            # Chromeブラウザの自動操作用ドライバーを起動
            self.web_driver = webdriver.Chrome(
                service=ChromeService(self.PATH_WEBDRIVER),  # chromedriverのパス
                options=self.get_driver_options())           # 動作オプション
            self.logging("Webドライバー準備完了")
            self.time_last_webdriver = time.time()  # 更新時刻を記録
        except Exception as e:
            # エラーが発生した場合はユーザーに通知
            self.logging(f"Webドライバーの準備に失敗: {str(e)}")
            messagebox.showerror("エラー", f"Webドライバーの準備に失敗しました:\n{str(e)}")
        
        # === 初期化完了 ===
        self.is_initializing = False  # 初期化フラグを解除
        self.label_proc["text"] = "[処理] 待機中..."
        self.btn_reconnect["state"] = "normal"  # 再接続ボタンを有効化

        # === バックグラウンド処理を開始 ===
        self.start_recconet_event()      # 再接続監視スレッドを起動
        self.start_interval_event()      # 定期処理スレッドを起動
        
        self.debug_logging("デバッグログの出力が有効です")
        # フォント変更のログ出力
        if self._deferred_font_log:
            self.logging(self._deferred_font_log)
        self.logging("起動しました")
        
        info_messages = [
            f"インターネット接続確認は{int(self.INTERVAL_ALIVE/60)}分周期で実行します",
            f"Webドライバー更新は{int(self.INTERVAL_WEBDRIVER/3600)}時間周期で実行します",
            f"ログは最大{self.MAX_LINES_LOG}行まで表示します。古いログは消去されます"
        ]
        
        for msg in info_messages:
            self.logging(msg)

    def _create_widgets(self):
        """UI要素を作成"""
        # 状態表示フレーム
        self.frame_state = tk.Frame(self, width=config.WINDOW_WIDTH, height=100, 
                                   borderwidth=1, padx=5, pady=5)
        
        self.label_datetime = tk.Label(self.frame_state, text="[日時] 起動処理中...",
                                       font=self.FONT_M, anchor=tk.W, padx=20)
        self.label_datetime.pack(fill=tk.X, side=tk.TOP)
        
        self.label_alive = tk.Label(self.frame_state, text="[接続] 起動処理中...",
                                   font=self.FONT_M, anchor=tk.W, padx=20)
        self.label_alive.pack(fill=tk.X, side=tk.TOP)
        
        self.label_proc = tk.Label(self.frame_state, text="[処理] 起動処理中...",
                                   font=self.FONT_M, anchor=tk.W, padx=20)
        self.label_proc.pack(fill=tk.X, side=tk.TOP)
        
        self.label_progress = tk.Label(self.frame_state, text="", font=self.FONT_M,
                                       anchor=tk.W, padx=20)
        self.label_progress.pack(fill=tk.X, side=tk.TOP)
        
        self.frame_state.pack(fill=tk.X, side=tk.TOP)
        
        # ボタン操作フレーム
        self.frame_btn_operation = tk.Frame(self, width=config.WINDOW_WIDTH, height=100,
                                           bd=1, padx=20, pady=5)
        
        self.btn_reconnect = tk.Button(self.frame_btn_operation, text="再接続",
                                      font=self.FONT_M, state="disable",
                                      command=self.btn_reconnect_clicked)
        self.btn_reconnect.pack(fill=tk.X, side=tk.LEFT)
        
        self.btn_reboot = tk.Button(self.frame_btn_operation, text="PC再起動",
                                    font=self.FONT_M, state="normal",
                                    command=self.btn_reboot_clicked)
        self.btn_reboot.pack(fill=tk.X, side=tk.LEFT)
        
        self.frame_btn_operation.pack(fill=tk.X, side=tk.TOP)
        
        # ログ表示フレーム
        self.frame_logging = tk.Frame(self, width=config.WINDOW_WIDTH, height=100,
                                     bd=1, padx=20, pady=10)
        
        self.scrbar_logging_x = tk.Scrollbar(self.frame_logging, orient=tk.HORIZONTAL)
        self.scrbar_logging_x.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.scrbar_logging_y = tk.Scrollbar(self.frame_logging, orient=tk.VERTICAL)
        self.scrbar_logging_y.pack(fill=tk.Y, side=tk.RIGHT)
        
        self.textbox_logging = tk.Text(self.frame_logging, undo=False,
                                       width=config.WINDOW_WIDTH, height=100,
                                       font=self.FONT_S, state="disable",
                                       xscrollcommand=self.scrbar_logging_x.set,
                                       yscrollcommand=self.scrbar_logging_y.set)
        self.textbox_logging.pack(fill=tk.X, side=tk.TOP, expand=True)
        self.scrbar_logging_x["command"] = self.textbox_logging.xview
        self.scrbar_logging_y["command"] = self.textbox_logging.yview
        
        self.frame_logging.pack(fill=tk.X, side=tk.TOP)

    def interval_proc(self):
        """インターバル処理"""
        if self.is_initializing:
            return
    
        self.update_label_datetime()
        
        if self.is_dialog:
            return
        
        self.textbox_logging.focus_set()
        
        if self.is_webdriver_updating:
            return
        
        if self.is_reconnecting:
            return
            
        if self.ENABLE_TRACEMALLOC_LOG:
            if self.INTERVAL_TRACEMALLOC < (time.time() - self.time_last_tracemalloc):
                self.update_tracemalloc()
            
        if self.INTERVAL_WEBDRIVER < (time.time() - self.time_last_webdriver):
            self.update_webdriver()
        
        if self.INTERVAL_ALIVE < (time.time() - self.time_last_alive):
            self.cnt_auto_recconet_error = 0
            self.update_label_alive()
            return
        
        if not self.is_alive:
            if self.cnt_auto_recconet_error < 3:
                self.recconet_event()

    def interval_event(self):
        """インターバルイベント"""
        self.interval_proc()
        self.after(1000, self.interval_event)

    def start_interval_event(self):
        """インターバルイベント起動"""
        th = threading.Thread(target=self.interval_event)
        th.start()

    def update_tracemalloc(self):
        """メモリ割当量の追跡"""
        if self.ENABLE_TRACEMALLOC_LOG:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            txt = "メモリ割当量TOP10:"
            for stat in top_stats[:10]:
                txt += "\n    "
                txt += str(stat)
            self.debug_logging(txt)
            self.time_last_tracemalloc = time.time()

    def reconnect_proc(self):
        """
        再接続処理（5ステップ）
        
        インターネット接続が切れたときに、自動的に再接続を試みます。
        1. Wi-Fiを一度遮断してリセット
        2. Wi-Fiを再開
        3. ブラウザを再起動（WebDriver更新）
        4. キャプティブポータル（認証ページ）で規約に同意
        5. 接続が復旧したか確認
        
        実行時間: 約30秒～数分
        """
        self.logging("再接続処理を開始しました")
        
        # ボタンとラベルを無効化（処理中を示す）
        self.btn_reconnect["state"] = "disable"
        self.label_proc["text"] = "[処理] 再接続しています..."
        
        # 進捗表示用のメッセージリスト
        text_indent = "       " 
        text_list = [
            "(1/5) Wi-Fiを遮断しています...",                              # Wi-FiをOFF
            "(2/5) Wi-Fiの遮断を解除しています...",                        # Wi-FiをON
            "(3/5) Webドライバーを更新しています...(この処理は数分かかることがあります)",  # ブラウザ再起動
            "(4/5) 認証ページを待機しています...",                          # 認証処理
            "(5/5) インターネット接続を確認しています..."                   # 接続確認
        ]
        
        # 5つのステップを順番に実行
        for i in range(5):
            self.label_progress["text"] = text_indent + text_list[i]
            if i == 0:  # ステップ1: Wi-Fi遮断
                self.block_wifi()  # sudo rfkill block wifi
                time.sleep(5)      # 5秒待機
            elif i == 1:  # ステップ2: Wi-Fi解除
                self.unblock_wifi()  # sudo rfkill unblock wifi
                time.sleep(5)         # 5秒待機
            elif i == 2:  # ステップ3: WebDriver更新
                self.update_webdriver()  # ブラウザを再起動
                time.sleep(1)
            elif i == 3:  # ステップ4: 認証処理
                self.accept_aup()  # キャプティブポータルで規約同意
                time.sleep(3)
            elif i == 4:  # ステップ5: 接続確認
                self.update_label_alive()  # インターネット接続を確認
        # 進捗表示をクリア
        self.label_progress["text"] = ""
        
        # === 処理結果を確認 ===
        if self.is_alive:
            # 成功: インターネット接続が復旧した
            self.cnt_auto_recconet_error = 0  # エラーカウントをリセット
            self.logging("再接続処理が完了しました")
        else:
            # 失敗: まだ接続できていない
            self.cnt_auto_recconet_error += 1  # エラー回数をカウント
            if self.cnt_auto_recconet_error < 3:
                # 3回未満ならリトライ可能
                self.logging(f"再接続処理が失敗しました。リトライします...({self.cnt_auto_recconet_error}/3)")
            else:
                # 3回失敗した場合は手動確認が必要
                self.logging("再接続処理のリトライ回数が規定回数を超えました")
                self.logging("Wi-Fi接続状態を確認するか、PCを再起動してください")
        
        # 状態をリセット
        self.label_proc["text"] = "[処理] 待機中..."
        self.btn_reconnect["state"] = "normal"  # ボタンを再有効化
        self.is_reconnecting = False  # 再接続フラグを解除
        self.debug_logging("再接続イベント終了")
        
    def recconet_event_loop(self):
        """再接続イベントループ"""
        while True:
            if self.is_reconnecting:
                self.reconnect_proc()
            time.sleep(1)

    def recconet_event(self):
        """再接続イベント"""
        if self.is_reconnecting:
            self.debug_logging("再接続イベント多重起動をブロック")
            return
        self.is_reconnecting = True
        self.debug_logging("再接続イベント起動")

    def start_recconet_event(self):
        """再接続イベント起動"""
        th = threading.Thread(target=self.recconet_event_loop)
        th.start()
        
    def debug_logging(self, msg):
        """デバッグログ出力"""
        if not self.ENABLE_DEBUG_LOG:
            return
        txt = "[DEBUG] " + msg
        self.logging(txt)

    def logging(self, msg):
        """ログ出力"""
        txt = lib_utils.get_datetime_text() + " " + msg
        if self.ENABLE_STDOUT_LOG:
            print(txt)
            return
        txt += "\n"
        self.textbox_logging["state"] = "normal"
        self.textbox_logging.insert(1.0, txt)
        numlines = int(self.textbox_logging.index('end - 1 line').split('.')[0])
        delcnt = numlines - self.MAX_LINES_LOG - 1
        while delcnt > 0:
            self.textbox_logging.delete("end-2l", "end-1c")
            delcnt -= 1
        self.textbox_logging["state"] = "disable"
        self.textbox_logging.update()
        if self.is_dialog:
            return
        self.textbox_logging.focus_set()
        
    def btn_reconnect_clicked(self):
        """再接続ボタンクリック"""
        if self.is_reconnecting:
            self.debug_logging("再接続イベント多重起動(クリック動作)をブロック")
            return
        self.logging("再接続を実行します")
        self.label_alive["text"] = "[接続] 再接続しています..."
        self.cnt_auto_recconet_error = 0
        self.recconet_event()

    def btn_reboot_clicked(self):
        """PC再起動ボタンクリック"""
        self.is_dialog = True
        res = messagebox.askquestion("確認", "PCを再起動しますか？")
        self.is_dialog = False
        if res == "yes":
            self.logging("PCを再起動します...")
            self.reboot_pc()
        
    def update_label_datetime(self):
        """日時表示更新"""
        text = "[日時] " + lib_utils.get_datetime_text()
        self.label_datetime["text"] = text

    def update_webdriver(self):
        """Webドライバー更新"""
        if self.is_webdriver_updating:
            self.debug_logging("Webドライバー更新の多重起動をブロック")
            return
        self.is_webdriver_updating = True
        self.time_last_webdriver = time.time()
        self.logging("Webドライバーを更新しています...(この処理は数分かかることがあります)")
        try:
            self.web_driver.close()
            self.web_driver.quit()
        except:
            pass
        gc.collect()
        time.sleep(1)
        self.web_driver = webdriver.Chrome(
            service=ChromeService(self.PATH_WEBDRIVER), 
            options=self.get_driver_options())
        self.logging("Webドライバー更新完了")
        self.time_last_webdriver = time.time()
        self.is_webdriver_updating = False
        time.sleep(1)
        
    def update_label_alive(self):
        """インターネット接続表示更新"""
        proc_text = self.label_proc["text"]
        self.label_proc["text"] = "[処理] インターネット接続を確認しています..."
        text = "[接続] インターネット接続"
        self.is_alive = self.is_internet_connection()
        if self.is_alive:
            text += "あり"
            self.cnt_auto_recconet_error = 0
        else:
            text += "なし"
            self.debug_logging("インターネット接続なし")
        self.time_last_alive = time.time()
        text += f" (最終更新時刻 {lib_utils.get_time_text()})"
        self.label_alive["text"] = text
        self.label_proc["text"] = proc_text
            
    def is_internet_connection(self, url="https://www.google.com"):
        """
        インターネット接続確認
        
        指定されたURL（デフォルト: google.com）にHEADリクエストを送信して
        接続状態を確認します。
        
        Returns:
            True: 接続成功（HTTPステータスコード200）
            False: 接続失敗またはタイムアウト
        """
        try:
            # HEADリクエスト（HTMLを取得せずにヘッダのみ）で接続確認
            response = requests.head(url, timeout=3)
            return response.status_code == 200  # 200 OKなら成功
        except:
            return False  # エラーが発生した場合は失敗

    def reboot_pc(self):
        """
        Raspbian（ラズビアン）を再起動
        
        sudo rebootコマンドを実行します。
        再起動まで約5秒かかります。
        
        Returns:
            戻り値（通常は使用しない）
        """
        # Raspbian用の再起動コマンド（sudo権限必要）
        cp = subprocess.run("sudo reboot", shell=True, capture_output=True, text=True)
        return cp.returncode

    def block_wifi(self):
        """
        Wi-Fi接続を遮断
        
        sudo rfkill block wlan0 を実行してWi-FiをOFFにします。
        wlan0のみをブロックし、wlan1（AP）には影響しません。
        再接続処理の第1ステップで使用されます。
        
        Returns:
            戻り値（0=成功、その他=失敗）
        """
        # システムコマンドを実行（sudo権限必要）
        # wlan0のみをブロック（wlan1のAPは影響を受けない）
        cp = subprocess.run("sudo rfkill block wlan0", shell=True, capture_output=True, text=True)
        txt = "Wi-Fiを遮断しています..."
        if cp.returncode == 0:
            txt += "OK"
        else:
            txt += f"Error (returncode={cp.returncode})"
        self.logging(txt)
        return cp.returncode
        
    def unblock_wifi(self):
        """
        Wi-Fi接続遮断を解除
        
        sudo rfkill unblock wlan0 を実行してWi-FiをONにします。
        wlan0のみをアンブロックし、wlan1（AP）には影響しません。
        再接続処理の第2ステップで使用されます。
        
        Returns:
            戻り値（0=成功、その他=失敗）
        """
        # システムコマンドを実行（sudo権限必要）
        # wlan0のみをアンブロック（wlan1のAPは影響を受けない）
        cp = subprocess.run("sudo rfkill unblock wlan0", shell=True, capture_output=True, text=True)
        txt = "Wi-Fiの遮断を解除しています..."
        if cp.returncode == 0:
            txt += "OK"
        else:
            txt += f"Error (returncode={cp.returncode})"
        self.logging(txt)
        return cp.returncode

    def accept_aup(self):
        """
        認証処理（キャプティブポータル処理）
        
        キャプティブポータルとは：
        - 公衆Wi-Fiなどで最初に訪問する自動で表示される認証ページ
        - このプログラムでは「規約に同意する」ボタンを自動クリック
        
        処理の流れ：
        1. テストページ（http://example.com）にアクセス
        2. キャプティブポータルが表示される
        3. 「ui_aup_accept_button」IDのボタンを検出
        4. ボタンをクリックして規約に同意
        """
        err_fg = False
        self.debug_logging("キャプティブポータルに接続しています...")
        
        # テストページにアクセス
        try:
            self.web_driver.get(self.TEST_PAGE_URL)  # ページを開く
            self.web_driver.implicitly_wait(15)       # 最大15秒待機
        except Exception as e:
            # エラーが発生した場合
            err_fg = True
            self.debug_logging("ページ遷移に失敗しました")
            self.debug_logging(str(e))

        if err_fg:
            # ページ遷移に失敗した場合は処理を中止
            self.logging("認証処理に失敗しました")
            return
            
        # 現在のURLを確認
        if self.web_driver.current_url == self.TEST_PAGE_CURRENT_URL:
            # すでに認証済み（テストページが表示されている）
            self.debug_logging("テストページを取得しました")
            pass
        else:
            # キャプティブポータルが表示されている
            try:
                self.debug_logging("認証処理中...")
                # 「規約に同意する」ボタンを検索（IDで指定）
                element = self.web_driver.find_element(By.ID, "ui_aup_accept_button")
                self.logging("規約に同意しています...")
                element.click()  # ボタンをクリック
            except:
                # ボタンが見つからない場合はスキップ
                pass

    def get_driver_options(self):
        """
        Webドライバー用動作オプション
        
        Chromiumブラウザの動作を制御するためのオプションを設定します。
        
        Returns:
            ChromeOptions: ブラウザオプション
        """
        options = webdriver.ChromeOptions()

        # バックグラウンド通信を無効化（メモリ節約）
        options.add_argument('--disable-background-networking')
        
        # ヘッドレスモード（画面を表示しない）
        options.add_argument('--headless=new')
        
        # 証明書エラーを無視（キャプティブポータル用）
        options.add_argument('--ignore-certificate-errors')
        
        # デフォルトブラウザのチェックを無効化
        options.add_argument('--no-default-browser-check')
        
        # IPヘッダの伝播を許可
        options.add_argument('--propagate-iph-for-testing')
        
        # SSLエラーを無視
        options.add_argument('--ignore-ssl-errors=yes')
        
        # 証明書エラーを再度無視
        options.add_argument('--ignore-certificate-errors')
        
        # 安全でない証明書を受け入れる（キャプティブポータル用）
        options.accept_insecure_certs = True
        
        # ページ読み込み戦略を設定（通常の読み込み）
        options.set_capability('pageLoadStrategy', 'normal')

        return options

    def _get_available_font(self, primary_font):
        """利用可能なフォントを取得（フォールバック付き）"""
        try:
            # 指定されたフォントが利用可能か確認
            _ = tk.font.Font(family=primary_font)
            return primary_font
        except Exception:
            # フォールバックフォントを試す
            for font_name in config.MONO_FONT_FALLBACK:
                try:
                    _ = tk.font.Font(family=font_name)
                    # ログは後で出力する（初期化中はまだ使えない）
                    return font_name
                except Exception:
                    continue
            # すべて失敗した場合は元のフォント名を返す
            return primary_font


def main():
    """
    メイン関数
    
    プログラムのエントリーポイントです。
    Tkinterウィンドウを作成し、アプリケーションを起動します。
    """
    win = tk.Tk()                               # ルートウィンドウを作成
    app = Application(master=win)                # アプリケーションクラスのインスタンスを作成
    app.mainloop()                              # イベントループを開始（ウィンドウが開き続ける）


if __name__ == "__main__":
    # このファイルが直接実行されたときにmain()を呼び出す
    main()


