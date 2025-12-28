import time
import threading
import requests
import subprocess
import gc
import tracemalloc
import tkinter as tk
import guest2lib
from datetime import datetime, timedelta, timezone
from tkinter import Text
from tkinter import font
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

class Application(tk.Frame):

	def __init__(self,master):
		super().__init__(master)
		
		# デバッグログを出力する場合はTrue; しない場合はFalse
		self.ENABLE_DEBUG_LOG = True
		
		# メモリ割当量を出力する場合はTrue; しない場合はFalse
		self.ENABLE_TRACEMALLOC_LOG = False
		
		# ログを標準出力に表示する場合はTrue; しない場合はFalse
		self.ENABLE_STDOUT_LOG = False
		
		# ログ表示行数最大値
		self.MAX_LINES_LOG = 1000
		
		# インターネット接続を確認する周期(秒)
		self.INTERVAL_ALIVE = 5 * 60

		# メモリ使用量を表示する周期(秒)
		self.INTERVAL_TRACEMALLOC = 30 * 60
		
		# Webドライバーを更新する周期(秒)
		self.INTERVAL_WEBDRIVER = 12 * 3600
		
		# Webドライバーのパス
		self.PATH_WEBDRIVER = "/usr/bin/chromedriver"
		
		# テストページURL
		self.TEST_PAGE_URL = "http://example.com"
		
		# テストページURL(確認用)
		self.TEST_PAGE_CURRENT_URL = "https://example.com/"

		# 等幅フォント
		self.MONO_FONT_FAMILY = "Ubuntu Mono"
		
		# 大フォント
		self.FONT_L = tk.font.Font(
			family = self.MONO_FONT_FAMILY,
			size = 14,
			weight = "normal")
		
		# 中フォント
		self.FONT_M = tk.font.Font(
			family = self.MONO_FONT_FAMILY,
			size = 12,
			weight = "normal")
		
		# 小フォント
		self.FONT_S = tk.font.Font(
			family = self.MONO_FONT_FAMILY,
			size = 9,
			weight = "normal")

		# インターネット接続ありならTrue
		self.is_alive = False

		# インターネット接続の最終確認時刻
		self.time_last_alive = 0

		# メモリ使用量の最終更新時刻
		self.time_last_tracemalloc = 0
		
		# Webドライバーの最終更新時刻
		self.time_last_webdriver = 0

		# 初期処理中はTrue
		self.is_initializing = True

		# Webドライバー更新中はTrue
		self.is_webdriver_updating = False
		
		# 再接続処理中はTrue
		self.is_reconnecting = False
		
		# ダイアログ表示中はTrue
		self.is_dialog = False
		
		# 再接続失敗カウント(3回超えたら自動再接続処理をスキップする)
		self.cnt_auto_recconet_error = 0
		
		# メモリ割り当ての追跡開始
		if self.ENABLE_TRACEMALLOC_LOG:
			tracemalloc.start()
		
		self.pack(fill = tk.BOTH)

		master.geometry("800x600")
		master.title("Guest2-Repeater")
		
		# 状態表示フレーム
		self.frame_state = tk.Frame(
			self,
			width = 800,
			height = 100,
			borderwidth = 1,
			padx = 5,
			pady = 5)
			
		# 状態表示フレーム > 日時ラベル
		self.label_datetime = tk.Label(
			self.frame_state,
			text = "[日時] 起動処理中...",
			font = self.FONT_M,
			anchor = tk.W,
			padx = 20)
		self.label_datetime.pack(fill = tk.X, side = tk.TOP)
		
		# 状態表示フレーム > 接続ラベル
		self.label_alive = tk.Label(
			self.frame_state,
			text = "[接続] 起動処理中...",
			font = self.FONT_M,
			anchor = tk.W,
			padx = 20)
		self.label_alive.pack(fill = tk.X, side = tk.TOP)
		
		# 状態表示フレーム > 処理ラベル
		self.label_proc = tk.Label(
			self.frame_state,
			text = "[処理] 起動処理中...",
			font = self.FONT_M,
			anchor = tk.W,
			padx = 20)
		self.label_proc.pack(fill = tk.X, side = tk.TOP)
		
		# 状態表示フレーム > 処理中ラベル
		self.label_progress = tk.Label(
			self.frame_state,
			text = "",
			font = self.FONT_M,
			anchor = tk.W,
			padx = 20)
		self.label_progress.pack(fill = tk.X, side = tk.TOP)
		
		# 状態表示フレームを配置
		self.frame_state.pack(fill = tk.X, side = tk.TOP)
		
		#ボタン操作フレーム
		self.frame_btn_operation = tk.Frame(
			self,
			width = 800,
			height = 100,
			bd = 1,
			padx = 20,
			pady = 5)
		
		# ボタン操作フレーム > [再接続]ボタン
		self.btn_reconnect = tk.Button(
			self.frame_btn_operation,
			text = "再接続",
			font = self.FONT_M,
			state = "disable",
			command = self.btn_reconnect_clicked)
		self.btn_reconnect.pack(fill = tk.X, side = tk.LEFT)

		# ボタン操作フレーム > [PC再起動]ボタン
		self.btn_reboot = tk.Button(
			self.frame_btn_operation,
			text = "PC再起動",
			font = self.FONT_M,
			state = "normal",
			command = self.btn_reboot_clicked)
		self.btn_reboot.pack(fill = tk.X, side = tk.LEFT)
		
		# ボタン操作フレームを配置
		self.frame_btn_operation.pack(fill = tk.X, side = tk.TOP)
		
		# ログ表示フレーム
		self.frame_logging = tk.Frame(
			self,
			width = 800,
			height = 100,
			bd = 1,
			padx = 20,
			pady = 10)
		
		# ログ表示フレーム > 水平スクロールバー
		self.scrbar_logging_x = tk.Scrollbar(self.frame_logging, orient = tk.HORIZONTAL)
		self.scrbar_logging_x.pack(fill = tk.X, side = tk.BOTTOM)

		# ログ表示フレーム > 垂直スクロールバー
		self.scrbar_logging_y = tk.Scrollbar(self.frame_logging, orient = tk.VERTICAL)
		self.scrbar_logging_y.pack(fill = tk.Y, side = tk.RIGHT)
		
		# ログ表示フレーム > ログテキストボックス
		self.textbox_logging = tk.Text(
			self.frame_logging,
			undo = False,
			width = 800,
			height = 100,
			font = self.FONT_S,
			state = "disable",
			xscrollcommand = self.scrbar_logging_x.set,
			yscrollcommand = self.scrbar_logging_y.set)
		self.textbox_logging.pack(fill = tk.X, side = tk.TOP, expand=True)
		self.scrbar_logging_x["command"] = self.textbox_logging.xview
		self.scrbar_logging_y["command"] = self.textbox_logging.yview
		
		# ログ表示フレームを配置
		self.frame_logging.pack(fill = tk.X, side = tk.TOP)
		
		# Webドライバーの準備
		self.logging("Webドライバーを準備しています...(この処理は数分かかることがあります)")
		self.web_driver = webdriver.Chrome(
			service = ChromeService(self.PATH_WEBDRIVER), 
			options = self.get_driver_options())
		self.logging("Webドライバー準備完了")
		self.time_last_webdriver = time.time()
		
		# 初期処理を完了させる
		self.is_initializing = False
		self.label_proc["text"] = "[処理] 待機中..."
		self.btn_reconnect["state"] = "normal"

		# 再接続イベント起動
		self.start_recconet_event()

		# インターバルイベント起動
		self.start_interval_event()
		
		self.debug_logging("デバッグログの出力が有効です")
		self.logging("起動しました")
		
		txt = "インターネット接続確認は"
		txt += str(int(self.INTERVAL_ALIVE/60))
		txt += "分周期で実行します"
		self.logging(txt)
		
		if self.ENABLE_TRACEMALLOC_LOG:
			txt = "メモリ使用量は"
			txt += str(int(self.INTERVAL_TRACEMALLOC/60))
			txt += "分周期で実行します"
			self.debug_logging(txt)
		
		txt = "Webドライバー更新は"
		txt += str(int(self.INTERVAL_WEBDRIVER/3600))
		txt += "時間周期で実行します"
		self.logging(txt)
		
		txt = "ログは最大"
		txt += str(self.MAX_LINES_LOG)
		txt += "行まで表示します。古いログは消去されます"
		self.logging(txt)
		
	def __del__(self):
		pass

	# インターバル処理
	def interval_proc(self):
		# 初期処理中は何もしない
		if self.is_initializing:
			return
	
		# 現在日時を更新
		self.update_label_datetime()
		
		# ダイアログ表示中は以降の定期処理をスキップする
		if self.is_dialog:
			return
		
		# ログ表示にフォーカスを与える
		self.textbox_logging.focus_set()
		
		# Webドライバー更新中は以降の定期処理をスキップする
		if self.is_webdriver_updating:
			return
		
		# 再接続処理中は以降の定期処理をスキップする
		if self.is_reconnecting:
			return
			
		# メモリ使用量更新
		if self.ENABLE_TRACEMALLOC_LOG:
			if (self.INTERVAL_TRACEMALLOC < (time.time() - self.time_last_tracemalloc)):
				self.update_tracemalloc()
			
		# Webドライバー更新
		if (self.INTERVAL_WEBDRIVER < (time.time() - self.time_last_webdriver)):
			self.update_webdriver()
		
		# インターネット接続確認
		if (self.INTERVAL_ALIVE < (time.time() - self.time_last_alive)):
			self.cnt_auto_recconet_error = 0
			self.update_label_alive()
			return
		
		# インターネット接続がない場合は再接続を試行する
		if not (self.is_alive):
			if (self.cnt_auto_recconet_error < 3):
				self.recconet_event()

	# インターバルイベント
	def interval_event(self):
		self.interval_proc()
		self.after(1000, self.interval_event)

	# インターバルイベント起動
	def start_interval_event(self):
		th = threading.Thread(target=self.interval_event)
		th.start()

	# メモリ割当量の追跡
	def update_tracemalloc(self):
		# メモリ割当量の追跡
		if self.ENABLE_TRACEMALLOC_LOG:
			snapshot = tracemalloc.take_snapshot()
			top_stats = snapshot.statistics('lineno')
			txt = "メモリ割当量TOP10:"
			for stat in top_stats[:10]:
				txt += "\n    "
				txt += str(stat)
			self.debug_logging(txt)
			self.time_last_tracemalloc = time.time()

	# 再接続処理
	def reconnect_proc(self):
		self.logging("再接続処理を開始しました")
		self.btn_reconnect["state"] = "disable"
		self.label_proc["text"] = "[処理] 再接続しています..."
		text_indent = "       " 
		text_list = []
		text_list.append("(1/5) Wi-Fiを遮断しています...")
		text_list.append("(2/5) Wi-Fiの遮断を解除しています...")
		text_list.append("(3/5) Webドライバーを更新しています...(この処理は数分かかることがあります)")
		text_list.append("(4/5) 認証ページを待機しています...")
		text_list.append("(5/5) インターネット接続を確認しています...")
		for i in range(5):
			self.label_progress["text"] = text_indent + text_list[i]
			#self.logging(text_list[i])
			match i:
				case 0:
					self.block_wifi()
					time.sleep(5)

				case 1:
					self.unblock_wifi()
					time.sleep(5)
					
				case 2:
					self.update_webdriver()
					time.sleep(1)
					
				case 3:
					self.accept_aup()
					time.sleep(3)
		
				case 4:
					self.update_label_alive()

				case _:
					pass
		self.label_progress["text"] = ""
		if self.is_alive:
			self.cnt_auto_recconet_error = 0
			self.logging("再接続処理が完了しました")
		else:
			self.cnt_auto_recconet_error += 1
			txt = "再接続処理が失敗しました。"
			if self.cnt_auto_recconet_error < 3:
				txt += "リトライします...("
				txt += str(self.cnt_auto_recconet_error)
				txt += "/3)"
				self.logging(txt)
			else:
				self.logging("再接続処理のリトライ回数が規定回数を超えました")
				self.logging("Wi-Fi接続状態を確認するか、PCを再起動してください")
		# 再接続モード解除
		self.label_proc["text"] = "[処理] 待機中..."
		self.btn_reconnect["state"] = "normal"
		self.is_reconnecting = False
		self.debug_logging("再接続イベント終了")
		
	# 再接続イベントループ
	def recconet_event_loop(self):
		while True:
			if self.is_reconnecting:
				target=self.reconnect_proc();
			time.sleep(1)

	# 再接続イベント
	def recconet_event(self):
		# 再接続イベントの多重起動を禁止
		if self.is_reconnecting:
			self.debug_logging("再接続イベント多重起動をブロック")
			return
		# 再接続モード有効
		self.is_reconnecting = True
		self.debug_logging("再接続イベント起動")

	# 再接続イベント起動
	def start_recconet_event(self):
		th = threading.Thread(target=self.recconet_event_loop)
		th.start()
		
	# デバッグログ出力
	def debug_logging(self, msg):
		if not (self.ENABLE_DEBUG_LOG):
			return
		txt = "[DEBUG] "
		txt += msg
		self.logging(txt)

	# ログ出力
	def logging(self, msg):
		txt = guest2lib.get_datetime_text()
		txt += " "
		txt += msg
		if self.ENABLE_STDOUT_LOG:
			print(txt)
			return
		txt += "\n"
		self.textbox_logging["state"] = "normal"
		self.textbox_logging.insert(1.0, txt)
		# 最大行数をオーバーしていたら古いログを削除する
		numlines = int(self.textbox_logging.index('end - 1 line').split('.')[0])
		delcnt = numlines - self.MAX_LINES_LOG - 1
		while delcnt > 0:
			self.textbox_logging.delete("end-2l", "end-1c")
			delcnt -= 1
		self.textbox_logging["state"] = "disable"
		self.textbox_logging.update()
		# ダイアログ表示中は以降の処理を行わない
		if self.is_dialog:
			return
		self.textbox_logging.focus_set()
		
	# 再接続ボタンクリック
	def btn_reconnect_clicked(self):
		# 再接続の多重起動を禁止
		if self.is_reconnecting:
			self.debug_logging("再接続イベント多重起動(クリック動作)をブロック")
			return
		self.logging("再接続を実行します")
		self.label_alive["text"] = "[接続] 再接続しています..."
		self.cnt_auto_recconet_error = 0
		self.recconet_event()

	# PC再起動ボタンクリック
	def btn_reboot_clicked(self):
		self.is_dialog = True
		res = messagebox.askquestion("確認", "PCを再起動しますか？")
		self.is_dialog = False
		if res == "yes":
			self.logging("PCを再起動します...")
			self.reboot_pc()
		
	# 日時表示更新
	def update_label_datetime(self):
		text = "[日時] "
		text += guest2lib.get_datetime_text()
		self.label_datetime["text"] = text

	# Webドライバー更新
	def update_webdriver(self):
		if self.is_webdriver_updating:
			self.debug_logging("Webドライバー更新の多重起動をブロック")
			return
		self.is_webdriver_updating = True
		self.time_last_webdriver = time.time()
		txt = "Webドライバーを更新しています..."
		txt += "(この処理は数分かかることがあります)"
		self.logging(txt)
		self.web_driver.close()
		self.web_driver.quit()
		gc.collect()
		time.sleep(1)
		self.web_driver = webdriver.Chrome(
			service = ChromeService(self.PATH_WEBDRIVER), 
			options = self.get_driver_options())
		self.logging("Webドライバー更新完了")
		self.time_last_webdriver = time.time()
		self.is_webdriver_updating = False
		time.sleep(1)
		
	# インターネット接続表示更新
	def update_label_alive(self):
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
		text += " (最終更新時刻 "
		text += guest2lib.get_time_text()
		text += ")"
		self.label_alive["text"] = text
		self.label_proc["text"] = proc_text
			
	# インターネット接続確認			
	def is_internet_connection(self, url = "https://www.google.com") -> bool:
		try:
			response = requests.head(url, timeout = 3)
			return response.status_code == 200
		except:
			return False

	# PCを再起動
	def reboot_pc(self):
		cp = subprocess.run(
			"reboot",
			shell = True,
			capture_output = True,
			text = True)
		return cp.returncode

	# Wi-Fi接続を遮断
	def block_wifi(self):
		# wlan0のみをブロック（wlan1のAPは影響を受けない）
		cp = subprocess.run(
			"rfkill block wlan0",
			shell = True,
			capture_output = True,
			text = True)
		txt = "Wi-Fiを遮断しています..."
		if cp.returncode == 0:
			txt += "OK"
		else:
			txt += "Error (returncode="
			txt += str(cp.returncode)
		self.logging(txt)
		return cp.returncode
		
	# Wi-Fi接続遮断を解除
	def unblock_wifi(self):
		# wlan0のみをアンブロック（wlan1のAPは影響を受けない）
		cp = subprocess.run(
			"rfkill unblock wlan0",
			shell = True,
			capture_output = True,
			text = True)
		txt = "Wi-Fiの遮断を解除しています..."
		if cp.returncode == 0:
			txt += "OK"
		else:
			txt += "Error (returncode="
			txt += str(cp.returncode)
		self.logging(txt)
		return cp.returncode


		
	# 認証処理
	def accept_aup(self):
		err_fg = False
		self.debug_logging("キャプティブポータルに接続しています...")
		try:
			self.web_driver.get(self.TEST_PAGE_URL)
			self.web_driver.implicitly_wait(15)
		except Exception as e:
			# エラー発生
			err_fg = True
			self.debug_logging("ページ遷移に失敗しました")
			self.debug_logging(str(e))

		if err_fg:
			self.logging("認証処理に失敗しました")
			return
			
		if (self.web_driver.current_url == self.TEST_PAGE_CURRENT_URL):
			self.debug_logging("テストページを取得しました")
			# リダイレクトが発生せずテストページが取得できたら何もしない
			pass
		else:
			try:
				self.debug_logging("認証処理中...")
				# 同意ボタンがあったらクリックする
				element = self.web_driver.find_element(
					By.ID,
					"ui_aup_accept_button")
				self.logging("規約に同意しています...")
				element.click()
			except:
				# 同意ボタンが見つからないなら何もしない
				pass

	# Webドライバー用動作オプション
	def get_driver_options(self):
		options = webdriver.ChromeOptions()

		# 拡張機能の更新、セーフブラウジングサービス、アップグレード検出、翻訳、UMAを含む
		# 様々なバックグラウンドネットワークサービスを無効
		options.add_argument('--disable-background-networking')

		# ヘッドレスモード
		options.add_argument('--headless=new')

		# SSL認証(この接続ではプライバシーが保護されません)を無効
		options.add_argument('--ignore-certificate-errors')

		# アドレスバー下に表示される「既定のブラウザとして設定」を無効
		options.add_argument('--no-default-browser-check')

		# Chromeに表示される青いヒントを非表示
		options.add_argument('--propagate-iph-for-testing')

		# SSLエラーを無視(注意！セキュリティリスク高！)
		options.add_argument('--ignore-ssl-errors=yes')
		options.add_argument('--ignore-certificate-errors')

		# 安全でない証明書を許可
		options.accept_insecure_certs = True

		# すべてのリソースをダウンロードするのを待つ
		options.set_capability('pageLoadStrategy', 'normal')

		return options
		

def main():
	win = tk.Tk()
	app = Application(master=win)
	app.mainloop()


if __name__ == "__main__":
	main()


