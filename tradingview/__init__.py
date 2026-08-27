"""Verbindung zwischen TradingView und diesem Projekt/Claude.

Zwei unabhaengige Wege, siehe data.py/screenshot.py:
- data.py: numerische Kurs-/Indikatordaten (tvDatafeed + tradingview_ta) als
  DataFrame/dict, analog zu den bestehenden yfinance-basierten data.py-Modulen
  im Projekt (z.B. ou_paper_backtest/data.py, cls_practical/data.py).
- screenshot.py: PNG-Screenshot eines TradingView-Charts per Playwright
  (gleiches Chromium-Muster wie OU-Modell-MT5-Bridge/scanner.py), fuer
  visuelle Analyse durch Claude.

Login (optional, fuer den TradingView-Pro-Account) liegt in _secrets.py und
liest aus .streamlit/secrets.toml (gitignored -- siehe secrets.toml.example
fuer die erwartete Struktur)."""
