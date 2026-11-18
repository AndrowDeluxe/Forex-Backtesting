"""Feste Einstellungen des Screeners. Gewichte und Regeln sind VORAB festgelegt und nicht optimiert
(Forward-Test, siehe ledger/FORWARD.md). Jede Aenderung an Gewichten oder Regeln -> VERSION hochzaehlen."""

from __future__ import annotations

from pathlib import Path

VERSION = "1.0"

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = REPO / "fusion_lab" / "data" / "screener"          # git-ignoriert
LEDGER_DIR = Path(__file__).resolve().parent / "ledger"         # git-getrackt
ARCHIVE_DIR = Path(__file__).resolve().parent / "archive"       # git-getrackt: jeder Lauf + Fundamentaldaten
SP500_CSV = REPO / "ou_paper_backtest" / "sp500_wiki.csv"
NASDAQ100_CSV = REPO / "ou_paper_backtest" / "nasdaq100_wiki.csv"

# Forward-Start: None = Probebetrieb (Ledger-Zeilen mit status "probe"). Wird erst nach Durchsicht der
# ersten Berichte durch den Nutzer gesetzt (Datum "YYYY-MM-DD"), danach nicht mehr aendern.
FORWARD_START: str | None = "2026-11-15"   # Nutzerbestaetigung 15.11.2026 (Version 1.0), nicht mehr aendern

# --- Universum ---------------------------------------------------------------------------------------
WATCHLIST_STOCKS = ["NVDA"]
N_DEEP_STOCKS = 10
STOCK_BENCHMARK = "SPY"

N_CRYPTO = 30
N_DEEP_CRYPTO = 5
CRYPTO_ALWAYS = ["BTC", "ETH"]
CRYPTO_BENCHMARK = "BTC"
# Stablecoins, Gold-/Fiat-Token, Wrapped-/Staking-Varianten: kein eigenstaendiges Krypto-Risiko
CRYPTO_EXCLUDE = {
    "USDT", "USDC", "DAI", "USDS", "USDE", "USD1", "FDUSD", "TUSD", "PYUSD", "RLUSD", "USDG", "USDY", "USDD",
    "BUSD", "GUSD", "USDP", "FRAX", "LUSD", "SUSDE", "USDX", "EURC", "EURS", "XAUT", "PAXG", "WBTC", "WETH",
    "STETH", "WSTETH", "WEETH", "CBBTC", "RETH", "BETH", "WBT", "LEO", "BGB", "FIGR_HELOC",
}

# --- Rohstoffe (Nutzerentscheid 18.11.2026: Kern-10, Signale + eigenes Ledger, Mo-Fr 23:15) ----------
# Eigene Version + eigener Forward-Start: der Rohstoff-Teil startet im Probebetrieb, unabhaengig von Aktien/Krypto.
VERSION_COMMODITIES = "1.0"
FORWARD_START_COMMODITIES: str | None = None     # setzt der Nutzer nach Durchsicht der ersten Berichte
COMMODITY_BENCHMARK = "DBC"                       # breiter Rohstoff-ETF
# Schluessel -> (Yahoo-Future, Name, Gruppe, CFTC-Code Disaggregated, News-Suchbegriff)
COMMODITIES = {
    "GOLD":     ("GC=F", "Gold", "Edelmetall", "088691", '"gold price"'),
    "SILBER":   ("SI=F", "Silber", "Edelmetall", "084691", '"silver price"'),
    "PLATIN":   ("PL=F", "Platin", "Edelmetall", "076651", '"platinum price"'),
    "KUPFER":   ("HG=F", "Kupfer", "Industriemetall", "085692", '"copper price" OR "copper prices"'),
    "WTI":      ("CL=F", "WTI-Öl", "Energie", "067651", '"oil prices" OR "WTI crude"'),
    "BRENT":    ("BZ=F", "Brent-Öl", "Energie", "06765T", '"Brent crude"'),
    "ERDGAS":   ("NG=F", "Erdgas (Henry Hub)", "Energie", "023651", '"natural gas prices"'),
    "WEIZEN":   ("ZW=F", "Weizen", "Agrar", "001602", '"wheat futures" OR "wheat prices"'),
    "MAIS":     ("ZC=F", "Mais", "Agrar", "002602", '"corn futures" OR "corn prices"'),
    "SOJA":     ("ZS=F", "Sojabohnen", "Agrar", "005602", '"soybean futures" OR "soybean prices"'),
}
COT_INDEX_WEEKS = 156       # COT-Index ueber 3 Jahre
# Absolute Punkte (nur 10 Titel -> kein Querschnitt). Vorab festgelegter Startwert, NICHT optimiert.
# cot ist contrarian: 100 - COT-Index (extremes Netto-Long der Fonds = Risiko).
WEIGHTS_COMMODITIES = {"trend": 30, "momentum": 25, "rel_staerke": 15, "cot": 20, "abstand_hoch": 10}

# --- Punktwert (0-100 je Baustein, Querschnitts-Perzentile) -------------------------------------------
WEIGHTS_STOCKS = {"trend": 15, "momentum": 15, "qualitaet": 15, "wachstum": 15, "bewertung": 15,
                  "bilanz": 10, "analysten": 15}
WEIGHTS_CRYPTO = {"trend": 25, "rel_staerke": 25, "liquiditaet": 15, "verwaesserung": 10, "funding": 10,
                  "abstand_hoch": 15}
FUNDAMENTALS_MAX_AGE_DAYS = 7

# Gesamtscore + Signal (Nutzerentscheid 15.11.2026, Prosper-Stil): >= 65 KAUFEN, <= 35 VERKAUFEN.
# Tiefen-Kandidaten: 70 % Kennzahlen-Score + 30 % News-Stimmung (Sentiment -2..+2 -> 0..100; Prosper
# gewichtet News ebenfalls mit 0,3). Ohne LLM-Teil = Kennzahlen-Score allein.
BUY_THRESHOLD = 65.0
SELL_THRESHOLD = 35.0
SENTIMENT_WEIGHT = 0.3

# --- Preisbereiche ----------------------------------------------------------------------------------
ATR_N = 14
PIVOT_WINDOW = 5            # Swing-Hoch/-Tief: Extrem in +-5 Kerzen
LOOKBACK_BARS = 260         # ~1 Jahr Tageskerzen
CLUSTER_ATR = 0.5           # Marken naeher als 0,5 ATR = ein Cluster
MIN_ZONE_ATR = 0.3          # Mindestbreite einer Zone
MAX_ZONE_ATR = 1.0          # Hoechstbreite einer Zone
A_MIN_ATR, A_MAX_ATR = 0.5, 2.5   # Ruecksetzer-Zone: Oberkante 0,5-2,5 ATR unter Kurs
B_MAX_ATR = 3.0             # Ausbruch-Trigger hoechstens 3 ATR ueber Kurs
B_BUFFER_ATR = 0.1
B_STOP_ATR = 1.5
STOP_BUFFER_ATR = 1.0       # Stopp = Zonenunterkante - 1 ATR
MIN_RR = 2.0
MAX_TARGETS = 3

# --- Forward-Auswertung -----------------------------------------------------------------------------
FILL_WINDOW = 10            # Handelstage, in denen die Zone/der Trigger erreicht werden muss
HOLD_MAX = 20               # Handelstage bis Zeitausstieg
RANK_HORIZONS = (5, 20, 60)
COST_BPS = {"aktien": 5.0, "krypto": 10.0, "rohstoffe": 5.0}   # Round-Trip

# --- LLM --------------------------------------------------------------------------------------------
LLM_MODEL = "sonnet"
LLM_TIMEOUT = 600
NEWS_HOURS = 72
NEWS_LIMIT = 10
