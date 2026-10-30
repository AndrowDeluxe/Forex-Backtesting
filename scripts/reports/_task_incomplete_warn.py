import sys
sys.path.insert(0, r"C:\Users\andre\Forex-Backtesting\scripts\reports")
from telegram_notify import send_telegram_message, SIGNATURE
send_telegram_message(SIGNATURE + "\n\n" + sys.argv[1])
