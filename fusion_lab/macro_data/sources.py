"""Abrufe je Quelle. Jede Funktion gibt ein Langformat zurueck: key, date, value.
Schluessel: <LAND>.<GROESSE>, z.B. JP.policy_rate, EUR.lev_net, US.2y.

Quellenwahl nach Live-Pruefung 30.10.2026: Die OECD-Inflationsreihen auf FRED sind
eingestellt (JP 2022, GB/CA 03/2025), darum Inflation ueber BIS und OECD direkt.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
FRED_API = "https://api.stlouisfed.org/fred/series/observations"
BIS_API = "https://stats.bis.org/api/v1/data"
OECD_API = "https://sdmx.oecd.org/public/rest/data"
ECB_API = "https://data-api.ecb.europa.eu/service/data"
CFTC_API = "https://publicreporting.cftc.gov/resource"
START = "2015-01-01"
TIMEOUT = 90

G8 = ["US", "EA", "GB", "JP", "CH", "AU", "CA", "NZ"]
OECD_AREA = {"USA": "US", "EA20": "EA", "GBR": "GB", "JPN": "JP", "CHE": "CH", "AUS": "AU", "CAN": "CA", "NZL": "NZ"}
BIS_AREA = {"US": "US", "XM": "EA", "GB": "GB", "JP": "JP", "CH": "CH", "AU": "AU", "CA": "CA", "NZ": "NZ"}

FRED = {
    "US.fed_funds": "DFF", "US.fed_target_upper": "DFEDTARU", "US.2y": "DGS2", "US.10y": "DGS10",
    "US.breakeven_10y": "T10YIE", "US.cpi_index": "CPIAUCSL", "US.core_cpi_index": "CPILFESL",
    "US.unemployment": "UNRATE", "US.payrolls": "PAYEMS", "US.gdp_real": "GDPC1",
    "US.retail_sales": "RSAFS", "US.trade_balance": "BOPGSTB",
    "EA.ecb_deposit": "ECBDFR",
    "GB.3m": "IR3TIB01GBM156N", "GB.10y": "IRLTLT01GBM156N",
    "JP.3m": "IR3TIB01JPM156N", "JP.10y": "IRLTLT01JPM156N",
    "CH.3m": "IR3TIB01CHM156N", "CH.10y": "IRLTLT01CHM156N",
    "AU.3m": "IR3TIB01AUM156N", "AU.10y": "IRLTLT01AUM156N",
    "CA.3m": "IR3TIB01CAM156N", "CA.10y": "IRLTLT01CAM156N",
    "NZ.3m": "IR3TIB01NZM156N", "NZ.10y": "IRLTLT01NZM156N",
    "GB.exports": "XTEXVA01GBM667S", "JP.exports": "XTEXVA01JPM667S", "CH.exports": "XTEXVA01CHM667S",
    "AU.exports": "XTEXVA01AUM667S", "CA.exports": "XTEXVA01CAM667S", "NZ.exports": "XTEXVA01NZM667S",
    "GB.trade_balance": "XTNTVA01GBM667S", "JP.trade_balance": "XTNTVA01JPM667S",
    "CH.trade_balance": "XTNTVA01CHM667S", "AU.trade_balance": "XTNTVA01AUM667S",
    "CA.trade_balance": "XTNTVA01CAM667S", "NZ.trade_balance": "XTNTVA01NZM667S",
    "MKT.vix": "VIXCLS", "MKT.hy_spread": "BAMLH0A0HYM2", "MKT.ig_spread": "BAMLC0A0CM",
    "MKT.nfci": "NFCI", "MKT.usd_broad": "DTWEXBGS", "MKT.wti": "DCOILWTICO",
}
ECB_YIELDS = {"EA.2y": "SR_2Y", "EA.10y": "SR_10Y"}
EUROSTAT_API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
# Zusammensetzung aendert sich: une_rt_m fuehrt EA21 (EA/EA20 leer), prc_hicp_manr endet 2025
# und wird von prc_hicp_minr abgeloest. Reihenfolge wichtig: das Spaetere gewinnt bei Ueberlappung.
EUROSTAT = [
    ("EA.unemployment", "une_rt_m", {"geo": "EA21", "s_adj": "SA", "age": "TOTAL", "unit": "PC_ACT", "sex": "T"}),
    ("EA.gdp_qoq", "namq_10_gdp", {"geo": "EA", "unit": "CLV_PCH_PRE", "s_adj": "SCA", "na_item": "B1GQ"}),
    ("EA.core_yoy", "prc_hicp_manr", {"geo": "EA", "coicop": "TOT_X_NRG_FOOD", "unit": "RCH_A"}),
    ("EA.services_yoy", "prc_hicp_manr", {"geo": "EA", "coicop": "SERV", "unit": "RCH_A"}),
    ("EA.core_yoy", "prc_hicp_minr", {"geo": "EA", "coicop18": "TOT_X_NRG_FOOD", "unit": "RCH_A"}),
    ("EA.services_yoy", "prc_hicp_minr", {"geo": "EA", "coicop18": "SERV", "unit": "RCH_A"}),
]

# CFTC-Marktcode -> Schluessel. TFF: Leveraged Funds + Asset Manager, Disaggregated: Managed Money.
CFTC_TFF = {"099741": "EUR", "096742": "GBP", "097741": "JPY", "092741": "CHF", "232741": "AUD",
            "090741": "CAD", "112741": "NZD", "098662": "USD", "13874+": "SPX", "20974+": "NDX",
            "042601": "UST2Y", "043602": "UST10Y"}
CFTC_DISAGG = {"088691": "GOLD", "084691": "SILVER", "067651": "WTI", "085692": "COPPER"}
CFTC_LAG_DAYS = 3  # Berichtsdatum Dienstag, veroeffentlicht Freitag

YF_MARKETS = {"MKT.gold": "GC=F", "MKT.silver": "SI=F", "MKT.brent": "BZ=F", "MKT.dxy": "DX-Y.NYB",
              "MKT.spx": "^GSPC", "MKT.ndx": "^NDX", "MKT.dax": "^GDAXI", "MKT.nikkei": "^N225"}
DUKA_FX = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD", "EURGBP", "EURJPY"]
MONTH_CODES = "FGHJKMNQUVXZ"


def _long(key: str, s: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"key": key, "date": s.index, "value": s.values})


def _fred_key() -> str:
    sys.path.insert(0, str(ROOT))
    from news_calendar._secrets import load_fred_api_key
    return load_fred_api_key()


def fetch_fred() -> pd.DataFrame:
    api_key = _fred_key()
    out = []
    for key, series in FRED.items():
        r = requests.get(FRED_API, params={"series_id": series, "api_key": api_key, "file_type": "json",
                                           "observation_start": START}, timeout=TIMEOUT)
        r.raise_for_status()
        obs = pd.DataFrame(r.json()["observations"])
        s = pd.Series(pd.to_numeric(obs["value"], errors="coerce").values, index=pd.to_datetime(obs["date"])).dropna()
        out.append(_long(key, s))
    return pd.concat(out, ignore_index=True)


def period_start(periods: pd.Series) -> pd.Series:
    """2026-09 -> 01.09.2026, 2026-Q3 -> 01.07.2026, 2026-09-14 -> 14.09.2026."""
    return periods.astype(str).map(lambda p: pd.Period(p).start_time if "Q" in p else pd.Timestamp(p))


def parse_bis(text: str, quantity: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text))
    df = df[df["REF_AREA"].isin(BIS_AREA)]
    return pd.DataFrame({"key": df["REF_AREA"].map(BIS_AREA) + "." + quantity,
                         "date": period_start(df["TIME_PERIOD"]),
                         "value": pd.to_numeric(df["OBS_VALUE"], errors="coerce")})


def fetch_bis() -> pd.DataFrame:
    areas = "+".join(BIS_AREA)
    start = pd.Timestamp(START)
    parts = []
    for flow, flt, quantity, period in [("WS_CBPOL", f"D.{areas}", "policy_rate", start.strftime("%Y-%m-%d")),
                                        ("WS_LONG_CPI", f"M.{areas}.771", "cpi_yoy", start.strftime("%Y-%m"))]:
        r = requests.get(f"{BIS_API}/{flow}/{flt}/all", params={"startPeriod": period, "format": "csv"},
                         timeout=TIMEOUT)
        r.raise_for_status()
        parts.append(parse_bis(r.text, quantity))
    out = pd.concat(parts, ignore_index=True)
    return out[out["key"] != "AU.cpi_yoy"]  # BIS nur quartalsweise, Australien kommt monatlich von der OECD


def _oecd(query: str, start: str) -> pd.DataFrame:
    r = requests.get(f"{OECD_API}/{query}", params={"startPeriod": start, "dimensionAtObservation": "AllDimensions"},
                     headers={"Accept": "application/vnd.sdmx.data+csv;version=2.0.0"}, timeout=TIMEOUT * 2)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    return df[df["REF_AREA"].isin(OECD_AREA)]


def _oecd_long(df: pd.DataFrame, quantity: str) -> pd.DataFrame:
    return pd.DataFrame({"key": df["REF_AREA"].map(OECD_AREA) + "." + quantity,
                         "date": period_start(df["TIME_PERIOD"]),
                         "value": pd.to_numeric(df["OBS_VALUE"], errors="coerce")})


def fetch_oecd() -> pd.DataFrame:
    """Kern-/Dienste-Inflation, Arbeitslosigkeit und BIP. Monatswerte vor Quartalswerten
    (Neuseeland meldet Inflation nur quartalsweise)."""
    areas = "+".join(OECD_AREA)
    parts = []
    cpi = _oecd(f"OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,/{areas}.M+Q.N.CPI.PA._TXCP01_NRG+SERV.N.GY", START[:7])
    for code, quantity in [("_TXCP01_NRG", "core_yoy"), ("SERV", "services_yoy")]:
        sub = cpi[cpi["EXPENDITURE"] == code]
        monthly = set(sub.loc[sub["FREQ"] == "M", "REF_AREA"])
        sub = sub[(sub["FREQ"] == "M") | ~sub["REF_AREA"].isin(monthly)]
        parts.append(_oecd_long(sub, quantity))
    au_cpi = _oecd(f"OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,/AUS.M.N.CPI.PA._T.N.GY", START[:7])
    parts.append(_oecd_long(au_cpi, "cpi_yoy"))
    une = _oecd(f"OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M,/{areas}..._Z.Y._T.Y_GE15..M+Q", START[:7])
    une = une[une["UNIT_MEASURE"].astype(str).str.startswith("PT")]
    monthly = set(une.loc[une["FREQ"] == "M", "REF_AREA"])
    parts.append(_oecd_long(une[(une["FREQ"] == "M") | ~une["REF_AREA"].isin(monthly)], "unemployment"))
    gdp = _oecd(f"OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD,/Q..{areas}.S1..B1GQ......G1.", "2015-Q1")
    parts.append(_oecd_long(gdp, "gdp_qoq"))
    out = pd.concat(parts, ignore_index=True)
    # Eurozone allein von Eurostat: leicht andere Werte (2,8 statt 2,9) wuerden sonst je Lauf als Revision zaehlen
    return out[~out["key"].str.startswith("EA.")]


def fetch_ecb() -> pd.DataFrame:
    """Euro-Staatsanleihen (AAA-Kurve), FRED hat fuer die Eurozone nichts Aktuelles."""
    out = []
    for key, tenor in ECB_YIELDS.items():
        r = requests.get(f"{ECB_API}/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.{tenor}",
                         params={"startPeriod": START, "format": "csvdata"}, timeout=TIMEOUT)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        s = pd.Series(pd.to_numeric(df["OBS_VALUE"], errors="coerce").values, index=pd.to_datetime(df["TIME_PERIOD"]))
        out.append(_long(key, s.dropna()))
    return pd.concat(out, ignore_index=True)


def parse_eurostat(payload: dict, key: str) -> pd.DataFrame:
    """JSON-stat: value ist {Position: Wert}, bei genau einer Reihe zaehlt die Position die Zeit."""
    position_to_period = {pos: period for period, pos in payload["dimension"]["time"]["category"]["index"].items()}
    obs = {position_to_period[int(pos)]: value for pos, value in payload["value"].items()}
    return pd.DataFrame({"key": key, "date": period_start(pd.Series(list(obs))), "value": list(obs.values())})


def fetch_eurostat() -> pd.DataFrame:
    """Eurozone, die der OECD-Abruf nicht liefert."""
    out = []
    for key, dataset, params in EUROSTAT:
        r = requests.get(f"{EUROSTAT_API}/{dataset}", params={"sinceTimePeriod": START[:4], **params}, timeout=TIMEOUT)
        r.raise_for_status()
        part = parse_eurostat(r.json(), key)
        if part.empty:
            raise ValueError(f"Eurostat {dataset} liefert fuer {key} nichts: Code geaendert?")
        out.append(part)
    return pd.concat(out, ignore_index=True)


def _cftc_rows(dataset: str, codes: list[str], fields: list[str]) -> pd.DataFrame:
    quoted = ",".join(f"'{c}'" for c in codes)
    r = requests.get(f"{CFTC_API}/{dataset}.json", params={
        "$where": f"cftc_contract_market_code in ({quoted}) AND report_date_as_yyyy_mm_dd >= '{START}T00:00:00.000'",
        "$select": ",".join(["cftc_contract_market_code", "report_date_as_yyyy_mm_dd", *fields]),
        "$order": "report_date_as_yyyy_mm_dd ASC", "$limit": 50000}, timeout=TIMEOUT)
    r.raise_for_status()
    return pd.DataFrame(r.json())


def cftc_long(rows: pd.DataFrame, names: dict[str, str], groups: dict[str, tuple[str, str]]) -> pd.DataFrame:
    """Netto je Gruppe plus Open Interest. date = Veroeffentlichung (Dienstag + 3 Tage),
    sonst wuerde ein Join den noch nicht bekannten Bericht verwenden."""
    published = pd.to_datetime(rows["report_date_as_yyyy_mm_dd"]).dt.tz_localize(None) + pd.Timedelta(days=CFTC_LAG_DAYS)
    name = rows["cftc_contract_market_code"].map(names)
    parts = [pd.DataFrame({"key": name + ".open_interest", "date": published,
                           "value": pd.to_numeric(rows["open_interest_all"])})]
    for label, (long_col, short_col) in groups.items():
        net = pd.to_numeric(rows[long_col]) - pd.to_numeric(rows[short_col])
        parts.append(pd.DataFrame({"key": name + f".{label}_net", "date": published, "value": net}))
    return pd.concat(parts, ignore_index=True)


def fetch_cftc() -> pd.DataFrame:
    tff = {"lev": ("lev_money_positions_long", "lev_money_positions_short"),
           "am": ("asset_mgr_positions_long", "asset_mgr_positions_short")}
    disagg = {"mm": ("m_money_positions_long_all", "m_money_positions_short_all")}
    fin = _cftc_rows("gpe5-46if", list(CFTC_TFF), ["open_interest_all", *[c for p in tff.values() for c in p]])
    com = _cftc_rows("72hh-3qpy", list(CFTC_DISAGG), ["open_interest_all", *[c for p in disagg.values() for c in p]])
    return pd.concat([cftc_long(fin, CFTC_TFF, tff), cftc_long(com, CFTC_DISAGG, disagg)], ignore_index=True)


def cot_index(net: pd.Series, weeks: int) -> pd.Series:
    """Position im Fenster: 0 = tiefster, 100 = hoechster Wert der letzten `weeks` Berichte."""
    low = net.rolling(weeks, min_periods=weeks).min()
    high = net.rolling(weeks, min_periods=weeks).max()
    return 100 * (net - low) / (high - low)


def fed_contracts(today: pd.Timestamp, months: int = 12) -> dict[str, str]:
    """Fed-Funds-Futures der naechsten Monate: Liefermonat -> Yahoo-Symbol."""
    first = today.to_period("M")
    return {str(p): f"ZQ{MONTH_CODES[p.month - 1]}{p.year % 100:02d}.CBT" for p in (first + i for i in range(months))}


def fetch_fed_futures() -> pd.DataFrame:
    """Implizierter Satz = 100 - Kurs, Schluessel US.ff_implied.<Liefermonat>.
    Die Wahrscheinlichkeit je Sitzung rechnet erst die Analytik (Schritt 2)."""
    import yfinance as yf
    out = []
    for month, symbol in fed_contracts(pd.Timestamp.now()).items():
        d = yf.download(symbol, period="1mo", progress=False, auto_adjust=True)
        if len(d):
            s = 100 - d["Close"].squeeze()
            s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
            out.append(_long(f"US.ff_implied.{month}", s.dropna()))
    if not out:
        raise ValueError("keine Fed-Funds-Futures erhalten")
    return pd.concat(out, ignore_index=True)


def fetch_yf_markets() -> pd.DataFrame:
    import yfinance as yf
    out = []
    for key, symbol in YF_MARKETS.items():
        d = yf.download(symbol, start=START, progress=False, auto_adjust=True)
        if len(d):
            s = d["Close"].squeeze().dropna()
            s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
            out.append(_long(key, s))
    return pd.concat(out, ignore_index=True)


def fetch_duka_fx() -> pd.DataFrame:
    """Tagesaktuelle FX-Schlusskurse, FRED H.10 laeuft rund eine Woche nach."""
    sys.path.insert(0, str(ROOT))
    from combined_strategy.data import fetch_timeframe
    today = pd.Timestamp.today()
    start = (today - pd.Timedelta(days=60)).strftime("%Y-%m-%d")
    out = []
    for pair in DUKA_FX:
        c = fetch_timeframe(pair, "D1", start, today.strftime("%Y-%m-%d"))["Close"]
        c.index = c.index.tz_convert(None).normalize()
        out.append(_long(f"FX.{pair}", c))
    return pd.concat(out, ignore_index=True)
