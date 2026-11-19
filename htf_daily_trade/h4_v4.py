"""H4-Manipulation Test 4: Nutzer-Kriterien aus der Handpruefung als Regeln (Plan freigegeben 16.11.2026).

    python -m htf_daily_trade.h4_v4            # Merkmale, IS-Beschreibung, Varianten (IS + OOS-Vergleich)

Grundsignal wie Test 3 (Sweep >= 2 Kerzen, Koerper zurueck, Einstieg Folgekerze, Stop am Docht der Signalkerze).
Neue Merkmale (ohne Vorgriff): Koerperanteil, Zahl geholter H4-Swings, Aktivitaet (Ø Spanne 6/12 Kerzen / ATR-Median
120), Druck (Gegenschluesse, echte Brueche der Vorkerze), ADX H4/Daily, RSI 14 und RSI Multi Length 10-20 (H4/Daily),
Bollinger 20/2, Stoch RSI, Lage in der HTF-Range (Daily-Swing-Range, 20 Tage, Vorwoche, Vormonat), Daily-Swing-Struktur,
Makro je Assetklasse (FX: M1/M2/M3/M6/M7/X3/X4 + G8-Abstand, „Makro-Punkte gegen“; Gold: Gold-Makro-Veto, M5, X3, X4,
M7, VIX), Kalender (Weihnachten 18.12.-08.01., US-/UK-Bankfeiertage samt Vortag).
Varianten: Q (Qualitaet) + A (Aktivitaet/Kalender) fest; L (ohne/DS/20T/VW/VM) x T (ohne/Trend-oder-Erschoepfung) x
M (ohne/<=2/<=3) x Uhrzeit (alle/ohne 23+07) x 9 Ausstiege, je FX und Metalle. Eine Position je Markt.
Gegenwaehrungs-Regime nicht verwendet: nur ex post definiert (fusion_lab.filters.gegenwaehrung, kein Signal).
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
from dateutil.easter import easter
from pandas.tseries.holiday import USFederalHolidayCalendar

from checklist_strategy.indicators import rsi, rsi_multi_length
from gold_smc_htf_ltf.structure import detect_fractal_swings
from htf_daily_trade.backtest_r import features, stats
from htf_daily_trade.c2_exit_varianten import konto
from htf_daily_trade.filter_matrix import MARKETS, METALS, MacroDirs, _adx
from htf_daily_trade.macro import G8_BASE
from htf_daily_trade.h4_manip import IS_END, IS_START, LOCK, OOS_END, Market, daily
from htf_daily_trade.h4_ny15 import h4_atr
from htf_daily_trade.h4_v3 import swing_structure
from htf_daily_trade.twin_trade import swap_r
from research_lock import Lock, deflated_sharpe

TZ = "Europe/Berlin"
MAX_N = 20
EXITS = {  # (Ziel, BE ab R, Teilgewinn-Anteil bei 1R, Zeit-BE nach Kerzen ohne 1R, max. Kerzen)
    "R3": ("R3", None, 0.0, None, 60), "TB": ("TB", None, 0.0, None, 60), "Z48": (None, None, 0.0, None, 12),
    "R3_BE1": ("R3", 1.0, 0.0, None, 60), "P50_R3": ("R3", 1.0, 0.5, None, 60), "P50_TB": ("TB", 1.0, 0.5, None, 60),
    "R3_ZBE3T": ("R3", None, 0.0, 18, 60), "R3_ZBE5T": ("R3", None, 0.0, 30, 60), "Z5T": (None, None, 0.0, None, 30)}
L_OPTS = ("ohne", "DS", "20T", "VW", "VM")
T_OPTS = ("ohne", "Trend_oder_Erschoepfung")
M_OPTS = ("ohne", "max2", "max3")
H_OPTS = ("alle", "ohne_23_07")
FX_MACRO = ("M1", "M2", "M3", "M6", "M7", "X3", "X4")
USER_LABELS = {  # Handpruefung 16.11. (Signalkerze Berlin): gueltig?
    ("XAUUSD", "2016-12-01 23:00"): False, ("XAUUSD", "2017-04-30 23:00"): True, ("EURUSD", "2017-11-30 11:00"): True,
    ("EURUSD", "2018-04-20 15:00"): False, ("EURUSD", "2018-09-10 07:00"): True, ("EURUSD", "2019-02-12 07:00"): True,
    ("EURUSD", "2019-04-26 11:00"): True, ("XAUUSD", "2019-05-01 07:00"): True, ("XAUUSD", "2020-05-19 07:00"): True,
    ("XAUUSD", "2020-05-26 11:00"): False, ("EURUSD", "2020-09-08 11:00"): False, ("XAUUSD", "2020-10-14 03:00"): True,
    ("XAUUSD", "2020-11-19 07:00"): True, ("XAUUSD", "2020-12-23 11:00"): True, ("EURUSD", "2021-01-26 07:00"): True,
    ("EURUSD", "2021-08-18 19:00"): True}
USER_ALT = [("XAUUSD", "2016-12-04"), ("XAUUSD", "2016-12-07"), ("EURUSD", "2020-11-09"), ("XAUUSD", "2020-05-27"),
            ("XAUUSD", "2020-09-28"), ("XAUUSD", "2020-10-07")]


# --------------------------------------------------------------------------- Kalender
def uk_holidays(years) -> set:
    out = set()
    for y in years:
        nd = pd.Timestamp(y, 1, 1)
        out.add(nd + pd.offsets.BDay(0))
        e = pd.Timestamp(easter(y))
        out |= {e - pd.Timedelta(days=2), e + pd.Timedelta(days=1)}
        may = pd.date_range(f"{y}-05-01", f"{y}-05-31", freq="W-MON")
        out |= {may[0], may[-1], pd.date_range(f"{y}-08-01", f"{y}-08-31", freq="W-MON")[-1]}
        out |= {pd.Timestamp(y, 12, 25), pd.Timestamp(y, 12, 26)}
    return out


def blocked_days(start: str = "2009-01-01", end: str = "2027-01-01") -> set:
    hol = set(USFederalHolidayCalendar().holidays(start, end)) | uk_holidays(range(2009, 2027))
    out = set()
    for d in hol:
        out |= {pd.Timestamp(d).normalize(), (pd.Timestamp(d) - pd.offsets.BDay(1)).normalize()}
    return out


def christmas(day: pd.Timestamp) -> bool:
    return (day.month == 12 and day.day >= 18) or (day.month == 1 and day.day <= 8)


# --------------------------------------------------------------------------- Simulation
def simulate(m: Market, k: int, sign: int, stop: float, spec, end_idx: int, cost: float):
    tgt_kind, be_at, part, zbe, max_bars = spec
    f = k + 1
    entry = m.o[f]
    risk = sign * (entry - stop)
    if not (risk > 0):
        return None
    tgt = None
    if tgt_kind == "R3":
        tgt = entry + sign * 3 * risk
    elif tgt_kind == "TB":
        tgt = m.target("TB", sign, entry, risk, k, f)
    last = min(end_idx, f + max_bars - 1)
    cur, done, realized, rest = stop, False, 0.0, 1.0
    one_r = entry + sign * risk
    reached = False
    px, j = None, f
    for j in range(f, last + 1):
        if (sign == 1 and m.l[j] <= cur) or (sign == -1 and m.h[j] >= cur):
            px = cur
            break
        hit1 = (sign == 1 and m.h[j] >= one_r) or (sign == -1 and m.l[j] <= one_r)
        if hit1 and not reached:
            reached = True
            if part > 0:
                realized += part * 1.0
                rest -= part
            if be_at is not None and be_at <= 1.0:
                cur = entry
        if tgt is not None and ((sign == 1 and m.h[j] >= tgt) or (sign == -1 and m.l[j] <= tgt)):
            px = tgt
            break
        if zbe is not None and not reached and j - f + 1 >= zbe:
            cur = entry if sign * (m.c[j] - entry) > 0 else cur   # Zeit-BE nur, wenn im Plus moeglich
            if sign * (m.c[j] - entry) <= 0:
                px = m.c[j]                                        # sonst: Trade nach x Tagen schliessen
                break
    if px is None:
        j, px = last, m.c[last]
    g = realized + rest * sign * (px - entry) / risk
    sw = swap_r(m.name, "long" if sign == 1 else "short", entry, risk, m.x.index[f].tz_localize(None),
                m.x.index[j].tz_localize(None))
    return g, g - cost / risk - sw, j


# --------------------------------------------------------------------------- Merkmale
class Ctx:
    """Vorberechnete Arrays je Markt (H4 + Daily) fuer features_at -- gemeinsam fuer Backtest und Live-Scanner."""

    def __init__(self, m: Market, end=OOS_END):
        self.m = m
        name = m.name
        h, l, c = m.h, m.l, m.c
        atr = h4_atr(m)
        self.atr_prev = np.r_[np.nan, atr[:-1]]
        atr_med = pd.Series(self.atr_prev).rolling(120, min_periods=60).median().to_numpy()
        rng_all = h - l
        self.act6 = pd.Series(rng_all).shift(1).rolling(6).mean().to_numpy() / atr_med
        self.act12 = pd.Series(rng_all).shift(1).rolling(12).mean().to_numpy() / atr_med
        cs = pd.Series(c)
        self.rsi_h4 = rsi(cs, 14).to_numpy()
        self.rsiml_h4 = rsi_multi_length(cs).to_numpy()
        r14 = rsi(cs, 14)
        self.stoch = ((r14 - r14.rolling(14).min()) / (r14.rolling(14).max() - r14.rolling(14).min())).to_numpy()
        bb_mid = cs.rolling(20).mean()
        bb_sd = cs.rolling(20).std(ddof=0)
        self.bb_up, self.bb_lo = (bb_mid + 2 * bb_sd).to_numpy(), (bb_mid - 2 * bb_sd).to_numpy()
        adx_h4, _ = _adx(m.x)
        self.adx_h4 = adx_h4.to_numpy()
        self.hs = swing_structure(m.x)
        d = daily(name).loc[:pd.Timestamp(end)]
        fx = features(d, MARKETS[name][1])
        self.ds = swing_structure(d)
        self.adx_d, _ = _adx(d)
        self.rsi_d, self.rsiml_d = rsi(d["Close"], 14).to_numpy(), rsi_multi_length(d["Close"]).to_numpy()
        sw = detect_fractal_swings(d.rename(columns=str.lower), k=2)
        self.last_sh = sw["swing_high_price"].where(sw["swing_high_confirmed"]).ffill().to_numpy()
        self.last_sl = sw["swing_low_price"].where(sw["swing_low_confirmed"]).ffill().to_numpy()
        self.hi20, self.lo20 = d["High"].rolling(20).max().to_numpy(), d["Low"].rolling(20).min().to_numpy()
        self.atr_d = fx["atr"].to_numpy()
        self.wk = d.resample("W-FRI").agg({"High": "max", "Low": "min"})
        self.mo = d.resample("ME").agg({"High": "max", "Low": "min"})
        self.pos = d.index.searchsorted(m.day) - 1
        self.wpos = self.wk.index.searchsorted(m.day - pd.to_timedelta(m.day.dayofweek, unit="D")) - 1
        self.mpos = self.mo.index.searchsorted(m.day.to_period("M").to_timestamp()) - 1


def features_at(ctx: Ctx, k: int, side: str, md: MacroDirs, gv, blocked: set) -> dict | None:
    """Merkmale des Grundsignals an H4-Kerze k (abgeschlossen) fuer eine Seite; None ohne Grundsignal."""
    m = ctx.m
    name = m.name
    o, h, l, c = m.o, m.h, m.l, m.c
    n = len(m.x)
    sign = 1 if side == "long" else -1
    rng = h[k] - l[k]
    if k < MAX_N + 1 or rng <= 0 or not np.isfinite(ctx.atr_prev[k]) or ctx.pos[k] < 25:
        return None
    p = ctx.pos[k]
    if sign == 1:
        ok = lambda q: l[k] < l[k - q:k].min() and min(o[k], c[k]) > l[k - q:k].min()
    else:
        ok = lambda q: h[k] > h[k - q:k].max() and max(o[k], c[k]) < h[k - q:k].max()
    if not ok(2):
        return None
    n_max = max(q for q in range(2, MAX_N + 1) if ok(q))
    lvl = l[k - 2:k].min() if sign == 1 else h[k - 2:k].max()
    ext = l[k] if sign == 1 else h[k]
    body = min(o[k], c[k]) if sign == 1 else max(o[k], c[k])
    swl = m.sw_lo if sign == 1 else m.sw_hi
    taken = 0
    for ci, bi, pr in reversed(swl):
        if ci > k - 1:
            continue
        if bi < k - 120:
            break
        if not ((ext < pr < body) if sign == 1 else (body < pr < ext)):
            continue
        seg = l[bi + 1:k] if sign == 1 else h[bi + 1:k]
        if len(seg) == 0 or (seg.min() > pr if sign == 1 else seg.max() < pr):
            taken += 1

    def lage(hi_, lo_):
        return (c[k] - lo_) / (hi_ - lo_) if np.isfinite(hi_) and np.isfinite(lo_) and hi_ > lo_ else np.nan

    last6 = slice(k - 6, k)
    gegen = (c[last6] < o[last6]) if sign == 1 else (c[last6] > o[last6])
    brueche = (c[k - 6:k] < l[k - 7:k - 1]) if sign == 1 else (c[k - 6:k] > h[k - 7:k - 1])
    day = m.day[k]
    sig_t = m.x.index[k]
    ein_t = m.x.index[k + 1] if k + 1 < n else sig_t + pd.Timedelta(hours=4)
    wk, mo, wpos, mpos = ctx.wk, ctx.mo, ctx.wpos, ctx.mpos
    r = {"markt": name, "klasse": "Metalle" if name in METALS else "FX", "seite": side, "k": k,
         "signal": sig_t.tz_convert(TZ), "einstieg": ein_t.tz_convert(TZ), "stunde": ein_t.tz_convert(TZ).hour,
         "kurs": o[k + 1] if k + 1 < n else c[k], "stop": ext, "marke": lvl,
         "spanne_atr": rng / ctx.atr_prev[k], "docht_anteil": sign * (body - ext) / rng,
         "koerper_anteil": abs(c[k] - o[k]) / rng, "n_sweep": n_max, "swings_geholt": taken,
         "schluss_unter_marke_atr": sign * (c[k] - lvl) / ctx.atr_prev[k],
         "akt6": ctx.act6[k], "akt12": ctx.act12[k], "gegendruck6": gegen.mean(), "brueche6": int(brueche.sum()),
         "adx_h4": ctx.adx_h4[k], "adx_d": ctx.adx_d.iat[p], "rsi_h4": ctx.rsi_h4[k], "rsiml_h4": ctx.rsiml_h4[k],
         "stochrsi_h4": ctx.stoch[k], "rsi_d": ctx.rsi_d[p], "rsiml_d": ctx.rsiml_d[p],
         "bb_aussen": bool(l[k] < ctx.bb_lo[k]) if sign == 1 else bool(h[k] > ctx.bb_up[k]),
         "lage_DS": lage(ctx.last_sh[p], ctx.last_sl[p]), "lage_20T": lage(ctx.hi20[p], ctx.lo20[p]),
         "lage_VW": lage(wk["High"].iat[wpos[k]], wk["Low"].iat[wpos[k]]) if wpos[k] >= 0 else np.nan,
         "lage_VM": lage(mo["High"].iat[mpos[k]], mo["Low"].iat[mpos[k]]) if mpos[k] >= 0 else np.nan,
         "range20_atr": (ctx.hi20[p] - ctx.lo20[p]) / ctx.atr_d[p] if ctx.atr_d[p] > 0 else np.nan,
         "feiertag": day.normalize() in blocked or christmas(day)}
    for f, v in (("DS", ctx.ds[p]), ("HS", ctx.hs[k - 1])):
        r[f] = "mit" if v * sign > 0 else "gegen" if v * sign < 0 else "neutral"
    mac = md.dirs(name, day)
    ex = md.extra(name, day)
    mac.update({"X3": ex["X3"], "X4": ex["X4"]})
    if name == "XAUUSD" and gv is not None:
        try:
            mac["GV"] = gv.direction(day)
        except Exception:
            mac["GV"] = 0
    for f, v in mac.items():
        v = int(np.sign(v or 0)) * sign
        r[f] = "mit" if v > 0 else "gegen" if v < 0 else "neutral"
    r["X1"] = ex["X1"]
    r["makro_gegen"] = sum(r[f] == "gegen" for f in FX_MACRO)
    g8 = md.g8
    gi = g8.index.searchsorted(day) - 1
    if gi >= 0:
        row = g8.iloc[gi]
        diff = (row[G8_BASE[name][0]] - row[G8_BASE[name][1]]) if name in G8_BASE else -row["USD"]
        r["g8_abstand"] = float(diff) * sign
    return r


def run_market(name: str, md: MacroDirs, gv, blocked: set) -> pd.DataFrame:
    m = Market(name, OOS_END)
    ctx = Ctx(m)
    end_idx = len(m.x) - 1
    start = int(m.x.index.searchsorted(pd.Timestamp(IS_START, tz="UTC")))
    rows = []
    for k in range(max(start, MAX_N + 1), end_idx):
        for side in ("long", "short"):
            r = features_at(ctx, k, side, md, gv, blocked)
            if r is None:
                continue
            sign = 1 if side == "long" else -1
            for ek, spec in EXITS.items():
                res = simulate(m, k, sign, r["stop"], spec, end_idx, m.cost)
                if res is not None:
                    r[f"g_{ek}"], r[f"r_{ek}"], r[f"j_{ek}"] = res
                    r[f"t_{ek}"] = m.x.index[res[2]].tz_convert(TZ)
            rows.append(r)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- Varianten
def masks(t: pd.DataFrame) -> dict:
    long = t["seite"] == "long"
    q = ((t["spanne_atr"] >= 0.86) & (t["docht_anteil"] >= 0.4) & (t["koerper_anteil"] <= 0.5)
         & (t["swings_geholt"] >= 1) & (t["schluss_unter_marke_atr"] >= 0.23))
    a = (t["akt12"] >= 0.8) & ~t["feiertag"]
    lage = {"ohne": pd.Series(True, index=t.index)}
    for key in ("DS", "20T", "VW", "VM"):
        col = t[f"lage_{key}"]
        lage[key] = (long & (col < 0.5)) | (~long & (col > 0.5))
    ersch = (long & (t["rsiml_h4"] < 25)) | (~long & (t["rsiml_h4"] > 75)) | t["bb_aussen"]
    trend = {"ohne": pd.Series(True, index=t.index), "Trend_oder_Erschoepfung": (t["DS"] == "mit") | ersch}
    gold = t["markt"] == "XAUUSD"
    silver = t["markt"] == "XAGUSD"
    gv = t.get("GV", pd.Series("neutral", index=t.index)).fillna("neutral")
    makro = {"ohne": pd.Series(True, index=t.index),
             "max2": (~t["klasse"].eq("Metalle") & (t["makro_gegen"] <= 2)) | (gold & (gv != "gegen")) | (silver & (t["X3"] != "gegen")),
             "max3": (~t["klasse"].eq("Metalle") & (t["makro_gegen"] <= 3)) | (gold & (gv != "gegen")) | silver}
    hour = {"alle": pd.Series(True, index=t.index), "ohne_23_07": ~t["stunde"].isin([23, 7])}
    return {"Q": q, "A": a, "L": lage, "T": trend, "M": makro, "H": hour}


def apply_busy(g: pd.DataFrame, ek: str) -> pd.DataFrame:
    keep, busy = [], {}
    for r in g.sort_values(["markt", "k"]).itertuples():
        if not np.isfinite(getattr(r, f"j_{ek}", np.nan)):
            continue
        if r.k + 1 <= busy.get(r.markt, -1):
            continue
        busy[r.markt] = getattr(r, f"j_{ek}")
        keep.append(r.Index)
    return g.loc[keep]


def summary(g: pd.DataFrame, ek: str, n_trials: int) -> dict:
    row = {}
    for per in ("IS", "OOS"):
        p = g[g["periode"] == per]
        st = stats(p[f"r_{ek}"])
        row.update({f"{per}_n": st.get("n", 0), f"{per}_R": st.get("mean_r", np.nan), f"{per}_t": st.get("t", np.nan),
                    f"{per}_brutto": p[f"g_{ek}"].mean()})
    i = g.loc[g["periode"] == "IS", f"r_{ek}"]
    row["dsr"] = deflated_sharpe(i.mean() / i.std(ddof=1), len(i), n_trials) if len(i) > 2 else np.nan
    gi = g[g["periode"] == "IS"]
    row["jahre+"] = f"{(gi.groupby(gi['einstieg'].dt.year)[f'r_{ek}'].mean() > 0).sum()}/{gi['einstieg'].dt.year.nunique()}"
    row["maerkte+"] = f"{(gi.groupby('markt')[f'r_{ek}'].mean() > 0).sum()}/{gi['markt'].nunique()}"
    return row


def main() -> None:
    lock = Lock(LOCK)
    n_var = len(L_OPTS) * len(T_OPTS) * len(M_OPTS) * len(H_OPTS) * len(EXITS) * 2
    if "Test 4" not in lock.log_path.read_text(encoding="utf-8"):
        lock.log_trials(n_var + 40, f"Test 4 (16.11.): Q+A fest x L5 x T2 x M3 x H2 x 9 Ausstiege x FX/Metalle = {n_var} + 40 Beschreibung")
    md = MacroDirs.full()
    try:
        from fusion_lab.filters.gold_macro_veto import GoldMacroVetoFilter
        gv = GoldMacroVetoFilter()
    except Exception as e:
        print("Gold-Makro-Veto nicht verfuegbar:", e)
        gv = None
    blocked = blocked_days()
    parts = []
    for name in MARKETS:
        parts.append(run_market(name, md, gv, blocked))
        print(f"  {name}: {len(parts[-1])} Signale", flush=True)
    t = pd.concat(parts, ignore_index=True)
    t["periode"] = np.where(t["signal"].dt.tz_localize(None) <= pd.Timestamp(IS_END) + pd.Timedelta(hours=23), "IS", "OOS")
    t.to_parquet("htf_daily_trade/h4_v4_signale.parquet", index=False)
    report(t, lock)


def report(t: pd.DataFrame, lock: Lock) -> None:
    pd.set_option("display.width", 260)
    i = t[t["periode"] == "IS"]
    print(f"\nLock {LOCK}: {lock.trials} Versuche. Signale IS {len(i)}, OOS {int((t.periode == 'OOS').sum())}")
    print("\n== IS-Beschreibung neue Merkmale (R3 ohne BE, Ø netto / brutto) ==")
    for col in ("koerper_anteil", "akt12", "gegendruck6", "adx_d", "adx_h4", "rsiml_h4", "rsi_d", "stochrsi_h4",
                "lage_DS", "lage_20T", "lage_VW", "lage_VM", "range20_atr", "g8_abstand"):
        q = pd.qcut(i[col], 5, duplicates="drop")
        g = i.groupby([q, "klasse"], observed=True).agg(n=("r_R3", "size"), netto=("r_R3", "mean"), brutto=("g_R3", "mean"))
        print(f"\n-- {col} --\n{g.unstack('klasse').round(3).to_string()}")
    for col in ("swings_geholt", "brueche6", "bb_aussen", "feiertag", "makro_gegen", "DS"):
        g = i.groupby([col, "klasse"], observed=True).agg(n=("r_R3", "size"), netto=("r_R3", "mean"), brutto=("g_R3", "mean"))
        print(f"\n-- {col} --\n{g.unstack('klasse').round(3).to_string()}")
    print("\n== Ausstiege IS (alle Signale, Ø netto) ==")
    print(pd.DataFrame({ek: i.groupby("klasse")[f"r_{ek}"].mean() for ek in EXITS}).T.round(3).to_string())

    lab = []
    for r in t.itertuples():
        key = (r.markt, r.signal.strftime("%Y-%m-%d %H:%M"))
        if key in USER_LABELS:
            lab.append({**r._asdict(), "gueltig": USER_LABELS[key]})
    lab = pd.DataFrame(lab)
    cols = ["markt", "seite", "signal", "gueltig", "spanne_atr", "docht_anteil", "koerper_anteil", "swings_geholt",
            "schluss_unter_marke_atr", "akt12", "adx_d", "rsiml_h4", "bb_aussen", "lage_DS", "lage_20T", "DS",
            "makro_gegen", "feiertag", "r_R3"]
    if len(lab):
        print("\n== Deine 16 bewerteten Trades mit Merkmalen ==\n" + lab[cols].round(2).to_string(index=False))

    mk = masks(t)
    rows, best = [], {}
    base = mk["Q"] & mk["A"]
    for kl in ("FX", "Metalle"):
        for lo, tr, ma, ho, ek in itertools.product(L_OPTS, T_OPTS, M_OPTS, H_OPTS, EXITS):
            sel = base & mk["L"][lo] & mk["T"][tr] & mk["M"][ma] & mk["H"][ho] & (t["klasse"] == kl)
            g = apply_busy(t[sel], ek)
            row = {"klasse": kl, "lage": lo, "trend": tr, "makro": ma, "uhr": ho, "ausstieg": ek,
                   **summary(g, ek, lock.trials)}
            rows.append(row)
    res = pd.DataFrame(rows)
    res.to_csv("htf_daily_trade/h4_v4_varianten.csv", index=False)
    show = ["lage", "trend", "makro", "uhr", "ausstieg", "IS_n", "IS_R", "IS_t", "IS_brutto", "OOS_n", "OOS_R", "OOS_t",
            "OOS_brutto", "dsr", "jahre+", "maerkte+"]
    for kl in ("FX", "Metalle"):
        r = res[(res["klasse"] == kl) & (res["IS_n"] >= 40)].sort_values("IS_t", ascending=False)
        print(f"\n== {kl}: Top 20 nach IS-t (von {len(r)}) ==\n" + r[show].head(20).round(3).to_string(index=False))
        best[kl] = r.iloc[0]
        for dim in ("lage", "trend", "makro", "uhr", "ausstieg"):
            print(f"Ø {dim}: " + res[res.klasse == kl].groupby(dim)[["IS_R", "OOS_R"]].mean().round(3).to_dict("index").__repr__())
    # Referenz ohne Q/A
    for kl in ("FX", "Metalle"):
        for lab_, sel in (("Grundsignal", t["klasse"] == kl), ("nur Q", mk["Q"] & (t["klasse"] == kl)),
                          ("Q+A", base & (t["klasse"] == kl))):
            g = apply_busy(t[sel], "R3")
            s = summary(g, "R3", lock.trials)
            print(f"{kl} {lab_:12s} R3: IS n {s['IS_n']} {s['IS_R']:+.3f} (brutto {s['IS_brutto']:+.3f}) | OOS n {s['OOS_n']} {s['OOS_R']:+.3f}")
    # Konto der besten je Klasse
    for kl, b in best.items():
        sel = (base & mk["L"][b.lage] & mk["T"][b.trend] & mk["M"][b.makro] & mk["H"][b.uhr] & (t["klasse"] == kl))
        g = apply_busy(t[sel], b.ausstieg).copy()
        g["datum"] = g["einstieg"].dt.tz_localize(None)
        g["exit_datum"] = g[f"t_{b.ausstieg}"].dt.tz_localize(None)
        k = konto(g.rename(columns={f"r_{b.ausstieg}": "r"})[["datum", "exit_datum", "r"]], lambda x: 0.01)
        print(f"\n{kl} beste ({b.lage}/{b.trend}/{b.makro}/{b.uhr}/{b.ausstieg}): Konto 1 % CAGR {k['cagr']:+.1%}, DD {k['max_dd']:.1%}")
        print(g.groupby(["markt", "periode"])[f"r_{b.ausstieg}"].agg(["size", "mean"]).unstack().round(3).to_string())
    # Nutzer-Alternativen
    print("\n== Deine Alternativ-Trades: findet die Regel sie? ==")
    for mkt, day in USER_ALT:
        g = t[(t["markt"] == mkt) & (t["signal"].dt.strftime("%Y-%m-%d") == day)]
        for r in g.itertuples():
            qa = bool(base.loc[r.Index])
            print(f"{mkt} {r.signal:%d.%m.%Y %H:%M} {r.seite:5s} Q+A {'ja ' if qa else 'nein'} | Spanne {r.spanne_atr:.2f} "
                  f"Docht {r.docht_anteil:.0%} Körper {r.koerper_anteil:.0%} Swings {r.swings_geholt} Schluss {r.schluss_unter_marke_atr:.2f} "
                  f"Akt {r.akt12:.2f} RSIML {r.rsiml_h4:.0f} DS {r.DS} | R3 {r.r_R3:+.2f}")
        if g.empty:
            print(f"{mkt} {day}: kein Signal der Grundregel")


if __name__ == "__main__":
    main()
