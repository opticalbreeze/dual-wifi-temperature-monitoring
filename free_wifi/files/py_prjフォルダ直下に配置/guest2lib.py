from datetime import datetime, timedelta, timezone

T_DELTA = timedelta(hours = 9)
T_JST = timezone(T_DELTA, "JST")

# ゼロ埋めの数値テキストを取得
def get_zero_padding_text(value, digit):
	txt = ""
	txv = str(value)
	cnt = digit - len(txv)
	for i in range(cnt):
		txt += "0"
	txt += txv
	return txt

# 日時文字列を取得
def get_datetime_text():
	now = datetime.now(T_JST)
	#txt = now.strftime("%Y-%m-%d %H:%M:%S")
	txt = ""
	txt += get_zero_padding_text(now.year, 4)
	txt += "-"
	txt += get_zero_padding_text(now.month, 2)
	txt += "-"
	txt += get_zero_padding_text(now.day, 2)
	txt += " "
	txt += get_zero_padding_text(now.hour, 2)
	txt += ":"
	txt += get_zero_padding_text(now.minute, 2)
	txt += ":"
	txt += get_zero_padding_text(now.second, 2)
	return txt

# 時刻文字列を取得
def get_time_text():
	now = datetime.now(T_JST)
	#txt = now.strftime("%H:%M:%S")
	txt = ""
	txt += get_zero_padding_text(now.hour, 2)
	txt += ":"
	txt += get_zero_padding_text(now.minute, 2)
	txt += ":"
	txt += get_zero_padding_text(now.second, 2)
	return txt
