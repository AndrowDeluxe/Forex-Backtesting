"""Noise-Area-Momentum und Oel (WTI) -- Nutzerauftrag 2026-10-14: "Teste auch hier die Zusammenhaenge mit Oel".

Muster: ORB-Oel-Arbeit (research_orb_oel_vergleich.py 11.10., research_orb_oel_filter.py 12.10.).
Vorgeschichte: knowledge/projects/zarattini-noise-area-momentum.md.

TEIL A -- Gegenprobe: dieselbe Strategie AUF Oel (Lock noise_area_oel_gegenprobe_20261014)
  Keine Optimierung, 4 feste Versuche: {Paper (VWAP-Stop), K2 (nur 1. Trade, halten bis Schluss)}
  x {Index-Uhr 09:30-16:00, Oel-Uhr 09:00-14:30 (NYMEX-Pit/Settlement, Entscheid 09:30-14:00)}.
  VM 1, Lookback 14 (Paper-Standard). Kosten OIL 4,0 bps Spread (ANNAHME, wie ORB-Oel) + Index-Slippage.
  Tage mit WTI < 10 $ raus (April 2020).
TEIL B -- Oel als Filter auf der Index-Strategie (Lock noise_area_oel_filter_20261014)
  Basis: eingefrorene Paper-Config (WINNERS, 11.10.). 8 vorab feste Varianten je Index:
    1 K20<0 aus     Tag aus, wenn Korr(Oel, Index, 20 Tage bis Vortag) < 0
    2 K40<0 aus     dito 40 Tage
    3 K20>=0 aus    Gegenstueck
    4 A60>0 aus     Tag aus, wenn Oel-Autokorrelation (Tagesrenditen, 60 Tage bis Vortag) > 0
    5 A60<=0 aus    Gegenstueck
    6 Oel gleich    Einstieg nur, wenn Oel seit 09:30 in Trade-Richtung lief
    7 Oel gegen     Einstieg nur, wenn Oel seit 09:30 gegen die Trade-Richtung lief
    8 Oel ruhig     Einstieg nur, wenn |Oel seit 09:30| unter seinem 60-Tage-Median (gleiche Uhrzeit)
    9 Oel bewegt    Gegenstueck zu 8 -- NACHTRAEGLICH ergaenzt, nachdem Teil C (inkl. Tresor) zeigte,
                    dass starke Oel-Tage die besten sind (dort mit Bewegung bis 16:00, Lookahead).
                    Vorbelastet, als Versuch mitgezaehlt.
  Auswahl NUR auf IS 2016-07-28..2022-12-31: Trades >= 50 % der Basis, Netto-Sharpe > Basis,
  beide IS-Haelften netto > 0; davon hoechster t. Sonst: kein Filter.
  OOS einmal, Tresor einmal (VORBELASTET: Tresor-Diagnose 12.10. und ORB-Oel-Kipp 2026 bekannt).
  Gewinner -> Forward ab 2026-10-15, Stichtag 2027-03-31.
TEIL C -- beschreibend (alle Perioden offen): Index-Trades der Paper-Config nach Oel-Regime,
  Oel-Richtung zum Einstieg und Oel-Tagesbewegung, je Periode.

  python scripts/research_noise_area_oel.py gegenprobe
  python scripts/research_noise_area_oel.py beschreibend
  python scripts/research_noise_area_oel.py filter
  python scripts/research_noise_area_oel.py evaluate      # ab 2027-03-31
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from noise_area_momentum.engine import DECISIONS, build_grid, metrics, run_general  # noqa: E402
from ny_open_orb.data import fetch_m1  # noqa: E402
from research_lock import Lock  # noqa: E402
from research_noise_area_momentum import (COST_RT, INSTRUMENTS, IS_END, IS_START, OOS_END, TRESOR_END,  # noqa: E402
                                          WINNERS, _periode, grid)
from research_orb_cancel_at_sl_and_hold import ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS  # noqa: E402

OUT = ROOT / "noise_area_momentum" / "results"
LOCK_A, LOCK_B = "noise_area_oel_gegenprobe_20261014", "noise_area_oel_filter_20261014"
FORWARD_START, EVAL_DATE = "2026-10-15", "2027-03-31"
COST_OIL = 4.0 + ENTRY_SLIPPAGE_BPS + EXIT_SLIPPAGE_BPS
MIN_PRICE = 10.0
OIL_DECISIONS = np.arange(30, 301, 30)       # Minuten nach 09:00 -> 09:30 .. 14:00
PERIODS = [("IS", IS_START, "2023-01-01"), ("OOS", "2023-01-01", "2025-10-01"), ("Tresor", "2025-10-01", "2026-10-01")]

_cache: dict = {}


def oil_grid(clock: str, end: str = TRESOR_END, refresh: bool = False) -> dict:
    key = (clock, end)
    if key not in _cache:
        m1 = fetch_m1("OIL", IS_START, end, force_refresh=refresh)
        g = build_grid(m1) if clock == "index" else build_grid(m1, start="09:00", n_bars=330, decisions=OIL_DECISIONS)
        ok = np.nanmin(g["low"], axis=1) >= MIN_PRICE
        _cache[key] = {k: (v if k == "decisions" else v[ok]) for k, v in g.items()}
    return _cache[key]


def lock(name: str) -> Lock:
    lk = Lock(name)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    return lk


def per_period(df: pd.DataFrame) -> list[dict]:
    out = []
    for name, a, b in PERIODS:
        sl = df[(df.index >= a) & (df.index < b)]
        d = sl[sl["valid"]]
        m = metrics(sl)
        out.append({"periode": name, "trades": int(d["trades"].sum()),
                    "brutto_bps_trade": d["gross_1x"].sum() / max(d["trades"].sum(), 1) * 1e4,
                    "netto_bps_trade": d["ret_net"].sum() / max(d["trades"].sum(), 1) * 1e4,
                    "sharpe": m.get("sharpe"), "t": m.get("t")})
    return out


# --- Teil A -------------------------------------------------------------------------------
GEGENPROBE = {"Paper (VWAP-Stop)": dict(exit="vwap", window="all"),
              "K2 (1. Trade, bis Schluss)": dict(exit="none", window="first")}


def stage_gegenprobe() -> None:
    lk = lock(LOCK_A)
    if lk.trials == 0:
        lk.log_trials(4, note="2 feste Configs x 2 Uhren auf OIL, keine Optimierung")
    h = lk.freeze({"configs": GEGENPROBE, "vm": 1.0, "lookback": 14, "kosten_oil_rt_bps": COST_OIL,
                   "uhren": {"index": "09:30-16:00", "oel": "09:00-14:30, Entscheid 09:30-14:00"}})
    for st in ("oos", "tresor"):
        if st not in lk._load()["unsealed"]:
            lk.unseal(st, h)
    rows = []
    for clock in ("index", "oel"):
        g = oil_grid(clock)
        for name, cfg in GEGENPROBE.items():
            df = run_general(g, vm=1.0, lookback=14, direction="mom", sides="both", cost_rt_bps=COST_OIL, **cfg)
            rows += [{"uhr": clock, "config": name, **r} for r in per_period(df)]
        # Marktstruktur: haelt ein Ausbruch bis zur 3. Entscheidung bis Schluss?
        from noise_area_momentum.engine import _sigma
        o, c = g["open"], g["close"]
        sig = _sigma(g, 14); pc = np.r_[np.nan, c[:-1, -1]]
        top, bot = np.fmax(o[:, 0], pc), np.fmin(o[:, 0], pc)
        ub, lb = top[:, None] * (1 + sig), bot[:, None] * (1 - sig)
        m = g.get("decisions", DECISIONS)[:4] - 1
        up, dn = (c[:, m] > ub[:, m]).any(1), (c[:, m] < lb[:, m]).any(1)
        held = np.where(up, c[:, -1] > ub[:, -1], c[:, -1] < lb[:, -1])
        s = pd.DataFrame({"brk": up ^ dn, "held": held}, index=g["dates"])
        s["p"] = _periode(s.index)
        print(f"Oel {clock}-Uhr: Ausbruch in den ersten 4 Entscheidungen haelt bis Schluss:",
              s[s.brk].groupby("p")["held"].mean().round(3).to_dict())
    rep = pd.DataFrame(rows)
    rep.to_csv(OUT / "oel_gegenprobe.csv", index=False)
    pd.set_option("display.width", 250)
    print(rep.round(3).to_string(index=False))


# --- Oel-Merkmale fuer Teil B/C ----------------------------------------------------------------
def oil_features(g_idx: dict, oil: dict) -> dict:
    """Alles auf die Index-Tage ausgerichtet. Oel mit Index-Uhr (09:30-16:00)."""
    dates = g_idx["dates"]
    oc = pd.Series(oil["close"][:, -1], index=oil["dates"])
    ic = pd.Series(g_idx["close"][:, -1], index=dates)
    rets = pd.DataFrame({"oil": oc.pct_change(), "idx": ic.pct_change()}).dropna()
    k20 = rets["oil"].rolling(20).corr(rets["idx"]).shift(1).reindex(dates)
    k40 = rets["oil"].rolling(40).corr(rets["idx"]).shift(1).reindex(dates)
    a60 = rets["oil"].rolling(60).apply(lambda x: pd.Series(x).autocorr(), raw=True).shift(1).reindex(dates)
    pos = pd.Index(oil["dates"]).get_indexer(dates)
    have = pos >= 0
    m = DECISIONS - 1
    move = np.full((len(dates), len(m)), np.nan)
    move[have] = oil["close"][pos[have]][:, m] / oil["open"][pos[have], [0]][:, None] - 1
    absm = pd.DataFrame(np.abs(move), index=dates)
    med = absm.rolling(60, min_periods=40).median().shift(1).to_numpy()
    day = np.full(len(dates), np.nan)
    day[have] = oil["close"][pos[have], -1] / oil["open"][pos[have], 0] - 1
    return {"k20": k20.to_numpy(), "k40": k40.to_numpy(), "a60": a60.to_numpy(), "move": move,
            "quiet": np.abs(move) < med, "day": day}


def filter_variants(f: dict) -> dict:
    nan_false = lambda x: np.nan_to_num(x, nan=0).astype(bool)  # noqa: E731
    mv = np.nan_to_num(f["move"], nan=0.0)
    have = ~np.isnan(f["move"])
    return {
        "1 K20<0 aus": {"gate": nan_false(f["k20"] >= 0)},
        "2 K40<0 aus": {"gate": nan_false(f["k40"] >= 0)},
        "3 K20>=0 aus": {"gate": nan_false(f["k20"] < 0)},
        "4 A60>0 aus": {"gate": nan_false(f["a60"] <= 0)},
        "5 A60<=0 aus": {"gate": nan_false(f["a60"] > 0)},
        "6 Oel gleich": {"long_ok": have & (mv > 0), "short_ok": have & (mv < 0)},
        "7 Oel gegen": {"long_ok": have & (mv < 0), "short_ok": have & (mv > 0)},
        "8 Oel ruhig": {"long_ok": have & f["quiet"], "short_ok": have & f["quiet"]},
        "9 Oel bewegt": {"long_ok": have & ~f["quiet"], "short_ok": have & ~f["quiet"]},
    }


def base_cfg(inst: str) -> dict:
    w = WINNERS[inst]
    return dict(vm=w["vm"], lookback=w["lookback"], direction="mom", exit="vwap", sides="both", window="all")


def stage_beschreibend() -> None:
    pd.set_option("display.width", 250)
    oil = oil_grid("index")
    for inst in INSTRUMENTS:
        g = grid(inst)
        f = oil_features(g, oil)
        t = pd.read_csv(OUT / f"diagnose_trades_{inst}.csv", parse_dates=["date"]).set_index("date")
        di = pd.Index(g["dates"]).get_indexer(t.index)
        j = np.searchsorted(DECISIONS, t["dec"].to_numpy())
        t["k20"] = f["k20"][di]
        t["oel_zum_einstieg"] = np.sign(f["move"][di, j]) * t["side"]
        t["oel_tag_abs"] = np.abs(f["day"][di]) * 1e4
        t["periode"] = _periode(t.index)
        t["k20_klasse"] = pd.cut(t["k20"], [-1, -0.2, 0, 0.2, 1], labels=["<-0,2", "-0,2..0", "0..0,2", ">0,2"])
        t["oel_richtung"] = t["oel_zum_einstieg"].map({1.0: "gleich", -1.0: "gegen", 0.0: "flach"})
        t["oel_tag_klasse"] = pd.qcut(t["oel_tag_abs"], 3, labels=["ruhig", "mittel", "stark"])
        print(f"\n######## {inst}: Brutto bps je Trade (Paper-Config) nach Oel-Merkmal ########")
        for col in ("k20_klasse", "oel_richtung", "oel_tag_klasse"):
            a = t.groupby(["periode", col], observed=True)["gross_bps"].agg(["mean", "count"])
            print(f"\n{col}:\n", a["mean"].round(2).unstack(0).join(a["count"].unstack(0), rsuffix=" n").to_string())
        print("\nK20 (Oel<->Index) Median je Periode:", t.groupby("periode")["k20"].median().round(3).to_dict())
        d = pd.DataFrame({"k20": f["k20"]}, index=g["dates"])
        print("K20 Median je Jahr (alle Tage):", d.groupby(d.index.year)["k20"].median().round(2).to_dict())
        t.to_csv(OUT / f"oel_beschreibend_{inst}.csv")


def stage_filter() -> None:
    lk = lock(LOCK_B)
    if lk.trials == 0:
        lk.log_trials(9 * len(INSTRUMENTS), note="8 feste Oel-Filter + 1 nachtraeglicher (9 Oel bewegt, vorbelastet) je Index")
    oil = oil_grid("index")
    pd.set_option("display.width", 250)
    winners, data = {}, {}
    for inst in INSTRUMENTS:
        g = grid(inst)
        fv = filter_variants(oil_features(g, oil))
        base = run_general(g, cost_rt_bps=COST_RT[inst], **base_cfg(inst))
        runs = {"0 Basis": base, **{k: run_general(g, cost_rt_bps=COST_RT[inst], **base_cfg(inst), **v)
                                    for k, v in fv.items()}}
        data[inst] = runs
        bi = lk.is_only(base)
        bm, btr = metrics(bi), bi.loc[bi.valid, "trades"].sum()
        rows = []
        for k, df in runs.items():
            di = lk.is_only(df)
            m = metrics(di)
            d = di[di.valid]
            half = d.index < pd.Timestamp("2019-10-01")
            rows.append({"variante": k, "trades": int(d["trades"].sum()), "sharpe": m["sharpe"], "t": m["t"],
                         "netto_bps_trade": d["ret_net"].sum() / max(d["trades"].sum(), 1) * 1e4,
                         "h1_netto_%": d.loc[half, "ret_net"].sum() * 100, "h2_netto_%": d.loc[~half, "ret_net"].sum() * 100})
        r = pd.DataFrame(rows)
        r["ok"] = (r["trades"] >= 0.5 * btr) & (r["sharpe"] > bm["sharpe"]) & (r["h1_netto_%"] > 0) & (r["h2_netto_%"] > 0) \
            & (r["variante"] != "0 Basis")
        print(f"\n===== {inst}: IS 2016-22 =====\n", r.round(3).to_string(index=False))
        ok = r[r["ok"]].sort_values("t", ascending=False)
        winners[inst] = ok.iloc[0]["variante"] if len(ok) else None
        print("IS-Gewinner:", winners[inst])
        r.to_csv(OUT / f"oel_filter_is_{inst}.csv", index=False)
    h = lk.freeze({"basis": "Paper-Config WINNERS 11.10.", "gewinner": winners,
                   "varianten": list(filter_variants({"k20": np.zeros(1), "k40": np.zeros(1), "a60": np.zeros(1),
                                                       "move": np.zeros((1, 12)), "quiet": np.zeros((1, 12), bool),
                                                       "day": np.zeros(1)}))})
    for st in ("oos", "tresor"):
        if st not in lk._load()["unsealed"]:
            lk.unseal(st, h)
    rows = []
    for inst in INSTRUMENTS:
        for k, df in data[inst].items():
            for r in per_period(df):
                rows.append({"inst": inst, "variante": k, "gewinner": k == winners[inst], **r})
    rep = pd.DataFrame(rows)
    rep.to_csv(OUT / "oel_filter_alle_perioden.csv", index=False)
    print("\nAlle Varianten, alle Perioden (nach dem Einfrieren, nur beschreibend):")
    print(rep.pivot_table(index=["inst", "variante"], columns="periode", values="netto_bps_trade")
          [["IS", "OOS", "Tresor"]].round(2).to_string())
    if any(winners.values()) and lk._load().get("forward") is None:
        lk.register_forward(FORWARD_START, EVAL_DATE, 10**6)
        print("Forward registriert ab", FORWARD_START, "| Stichtag", EVAL_DATE)


def stage_evaluate() -> None:
    lk = lock(LOCK_B)
    st = lk._load()
    win = st["frozen"]["config"]["gewinner"]
    lk.unseal("forward", st["frozen"]["hash"])
    oil = oil_grid("index", end=EVAL_DATE, refresh=True)
    for inst in INSTRUMENTS:
        if not win.get(inst):
            continue
        g = build_grid(fetch_m1(inst, IS_START, EVAL_DATE, force_refresh=True))
        fv = filter_variants(oil_features(g, oil))
        for k, df in (("0 Basis", run_general(g, cost_rt_bps=COST_RT[inst], **base_cfg(inst))),
                      (win[inst], run_general(g, cost_rt_bps=COST_RT[inst], **base_cfg(inst), **fv[win[inst]]))):
            sl = df[df.index >= FORWARD_START]
            d = sl[sl.valid]
            print(inst, k, "Trades", int(d.trades.sum()), "netto bps/Trade",
                  round(d.ret_net.sum() / max(d.trades.sum(), 1) * 1e4, 2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"gegenprobe": stage_gegenprobe, "beschreibend": stage_beschreibend, "filter": stage_filter,
     "evaluate": stage_evaluate}[sys.argv[1]]()
