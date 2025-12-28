from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from time import sleep

path= "/usr/bin/chromedriver"

options = webdriver.ChromeOptions()

#ユーザーデータとプロファイルを指定(これがないと起動しない？)
#options.add_argument('--user-data-dir = ~/selenium_test/UserData')
#options.add_argument('--profile-directory = Profile1')

#拡張機能の更新、セーフブラウジングサービス、アップグレード検出、翻訳、UMAを含む
#様々なバックグラウンドネットワークサービスを無効
options.add_argument('--disable-background-networking')

#ヘッドレスモード
#options.add_argument('--headless=new')

#SSL認証(この接続ではプライバシーが保護されません)を無効
options.add_argument('--ignore-certificate-errors')

#アドレスバー下に表示される「既定のブラウザとして設定」を無効
options.add_argument('--no-default-browser-check')

#Chromeに表示される青いヒントを非表示
options.add_argument('--propagate-iph-for-testing')

#SSLエラーを無視(注意！セキュリティリスク高！)
options.add_argument('--ignore-ssl-errors=yes')
options.add_argument('--ignore-certificate-errors')

#安全でない証明書を許可
options.accept_insecure_certs = True

# すべてのリソースをダウンロードするのを待つ
options.set_capability('pageLoadStrategy', 'normal')

#options.add_experimental_option("excludeSwitches", ["enable-automation"])

print("webドライバーを準備しています...")
driver = webdriver.Chrome(service = ChromeService(path), options = options)
print("webドライバーを準備完了")

try:
	driver.get("http://example.com")
	driver.implicitly_wait(15)
	print(driver.current_url)

	if (driver.current_url == "https://example.com/"):
		# リダイレクトが発生せずexample.comページを取得できた場合は何もしない
		pass
	else:
		try:
			# 同意ボタンがあったらクリックする
			element = driver.find_element(By.ID, "ui_aup_accept_button")
			print("同意ボタンあり")
			element.click()
		except:
			# 同意ボタンが見つからないなら何もしない
			print("同意ボタンなし")
			pass

# エラーが発生した時はエラーメッセージを吐き出す。
except Exception as e:
    print(e)
    print("エラーが発生しました。")

# 最後にドライバーを終了する
finally:
    driver.close()
    driver.quit()

