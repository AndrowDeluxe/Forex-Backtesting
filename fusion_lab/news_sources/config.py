"""Universum, Quellen und Pfade der News-/Sentiment-Schicht (Plan 21.11.2026, Prosper Lektion 5).

Universum = Prosper-Kurs-Watchlist + Forex-Kern, damit die FX-Historie ab Tag 1 mitlaeuft.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEDGER_DIR = Path(__file__).resolve().parent / "ledger"          # im Git
LEDGER = LEDGER_DIR / "werte.csv"
DATA_DIR = REPO / "fusion_lab" / "data" / "news_sources"         # git-ignoriert: Rohdaten je Lauf
LATEST = DATA_DIR / "latest.json"

UA = {"User-Agent": "Mozilla/5.0 (macro research script)"}
TIMEOUT = 25
LLM_MODEL = "sonnet"
LLM_TIMEOUT = 900
NEWS_HOURS = 24
NEWS_LIMIT = 8
SOCIAL_LIMIT = 10

# Symbol -> Klasse, Google-News-Suche, StockTwits-Symbol, Alpha-Vantage-Ticker, Kurs (yfinance), Waehrungen,
# SEC-CIK (nur US-Aktien), Subreddits
UNIVERSE: dict[str, dict] = {
    "SPY":    {"klasse": "aktien", "news": "S&P 500 stock market", "st": "SPY", "av": "SPY", "kurs": "SPY",
               "ccy": ["USD"], "subs": ["stocks", "wallstreetbets"]},
    "QQQ":    {"klasse": "aktien", "news": "Nasdaq 100 tech stocks", "st": "QQQ", "av": "QQQ", "kurs": "QQQ",
               "ccy": ["USD"], "subs": ["stocks", "wallstreetbets"]},
    "AAPL":   {"klasse": "aktien", "news": "Apple AAPL stock", "st": "AAPL", "av": "AAPL", "kurs": "AAPL",
               "cik": 320193, "subs": ["stocks", "wallstreetbets"]},
    "NVDA":   {"klasse": "aktien", "news": "Nvidia NVDA stock", "st": "NVDA", "av": "NVDA", "kurs": "NVDA",
               "cik": 1045810, "subs": ["stocks", "wallstreetbets"]},
    "TSLA":   {"klasse": "aktien", "news": "Tesla TSLA stock", "st": "TSLA", "av": "TSLA", "kurs": "TSLA",
               "cik": 1318605, "subs": ["stocks", "wallstreetbets"]},
    "BTC":    {"klasse": "krypto", "news": "Bitcoin price", "st": "BTC.X", "av": "CRYPTO:BTC", "kurs": "BTC-USD",
               "subs": ["CryptoCurrency", "Bitcoin"]},
    "ETH":    {"klasse": "krypto", "news": "Ethereum price", "st": "ETH.X", "av": "CRYPTO:ETH", "kurs": "ETH-USD",
               "subs": ["CryptoCurrency", "ethereum"]},
    "SOL":    {"klasse": "krypto", "news": "Solana SOL price", "st": "SOL.X", "av": "CRYPTO:SOL", "kurs": "SOL-USD",
               "subs": ["CryptoCurrency", "solana"]},
    "EURUSD": {"klasse": "fx", "news": "EUR/USD euro dollar", "st": "EURUSD", "av": "FOREX:EUR", "kurs": "EURUSD=X",
               "ccy": ["EUR", "USD"], "subs": ["Forex"]},
    "GBPUSD": {"klasse": "fx", "news": "GBP/USD pound sterling", "st": "GBPUSD", "av": "FOREX:GBP", "kurs": "GBPUSD=X",
               "ccy": ["GBP", "USD"], "subs": ["Forex"]},
    "USDJPY": {"klasse": "fx", "news": "USD/JPY yen", "st": "USDJPY", "av": "FOREX:JPY", "kurs": "JPY=X",
               "ccy": ["USD", "JPY"], "subs": ["Forex"]},
    "AUDUSD": {"klasse": "fx", "news": "AUD/USD Australian dollar", "st": "AUDUSD", "av": "FOREX:AUD", "kurs": "AUDUSD=X",
               "ccy": ["AUD", "USD"], "subs": ["Forex"]},
    "USDCAD": {"klasse": "fx", "news": "USD/CAD Canadian dollar loonie", "st": "USDCAD", "av": "FOREX:CAD", "kurs": "CAD=X",
               "ccy": ["USD", "CAD"], "subs": ["Forex"]},
    "USDCHF": {"klasse": "fx", "news": "USD/CHF Swiss franc", "st": "USDCHF", "av": "FOREX:CHF", "kurs": "CHF=X",
               "ccy": ["USD", "CHF"], "subs": ["Forex"]},
    "XAUUSD": {"klasse": "fx", "news": "gold price", "st": "XAUUSD", "av": "FOREX:XAU", "kurs": "GC=F",
               "ccy": ["USD"], "subs": ["Forex", "Gold"]},
}

# Offizielle Quellen: Zentralbank-RSS je Waehrung (live geprueft 21.11.2026)
CENTRAL_BANKS = {
    "USD": ("Fed", "https://www.federalreserve.gov/feeds/press_all.xml"),
    "EUR": ("EZB", "https://www.ecb.europa.eu/rss/press.html"),
    "GBP": ("BoE", "https://www.bankofengland.co.uk/rss/news"),
    "JPY": ("BoJ", "https://www.boj.or.jp/en/rss/whatsnew.xml"),
}
CB_DAYS = 3          # Meldungen der letzten n Tage
EDGAR_DAYS = 5
EDGAR_FORMS = ("8-K", "10-Q", "10-K", "6-K")

# Marktweite Zahlen -> auf welches Symbol sie im Ledger gemessen werden
MARKET_WIDE = {"cnn_fear_greed": "SPY", "cnn_put_call": "SPY", "krypto_fear_greed": "BTC"}

# Quellen, die nur im Tageslauf abgefragt werden (Abfragelimit)
DAILY_ONLY = {"alphavantage"}
AV_SCALE = 0.35      # Alpha-Vantage-Score ~ -0,35..+0,35 -> auf -1..+1

GROUPS = ("news", "social", "offiziell")   # Quellgruppen fuer die Claude-Einordnung
MIN_OBS = 60                               # ab so vielen Beobachtungen je Quelle ist die Auswertung aussagekraeftig
HORIZONS = (1, 3, 5, 10)                   # Handelstage
