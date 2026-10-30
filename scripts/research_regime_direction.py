"""Richtungsbacktest: Regime der Wachstums-Inflations-Karte -> Richtung je Asset.

Regel (vorab festgelegt, Nutzerwunsch 28.10.2026): Fuer jedes Asset und jedes
Regime wird die Richtung (long/short) NUR auf IS als Vorzeichen der mittleren
Tagesrendite in diesem Regime bestimmt. Danach haelt die Strategie jedes Asset
taeglich in der Richtung des aktuell gueltigen Regimes (Labels sind point-in-
time: ein Print gilt ab der Folgesitzung). Regime ohne IS-Beobachtung -> flat.
Gewichtung: Kehrwert der IS-Volatilitaet (gleiches Risiko je Asset), Korb =
Mittel ueber verfuegbare Assets. Kosten 2 bps je Richtungswechsel und Asset.

Overfitting-Sperre (Lock "regime_direction"): IS 2000-09-01..2014-12-31,
OOS ..2025-10-20, Tresor ..2026-10-20 (letzte 12 Monate). Varianten = die drei
Linsen der Karte (joint/change/signs) -> 3 Versuche, Auswahl nach IS-Sharpe.

    python -m scripts.research_regime_direction --stage is|oos|tresor
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from fusion_lab.macro_regime import model as m  # noqa: E402
from fusion_lab.macro_regime.universe import GROUPS, universe_returns  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402

STRATEGY = "regime_direction"
SPLIT = ("2000-09-01", "2014-12-31", "2025-10-20", "2026-10-20")
LENSES = ("joint", "change", "signs")
COST = 2 / 10_000
OUT = Path(__file__).resolve().parents[1] / "fusion_lab" / "data" / "macro_regime"


def directions(rets: pd.DataFrame, lab: pd.Series) -> pd.DataFrame:
    """Vorzeichen der mittleren Rendite je Regime (Zeilen) und Asset (Spalten)."""
    return np.sign(rets.groupby(lab).mean())


def run(rets: pd.DataFrame, lab: pd.Series, dirs: pd.DataFrame, vol: pd.Series):
    pos = dirs.reindex(lab.values).set_axis(lab.index).reindex(columns=rets.columns).fillna(0.0)
    pos = pos.reindex(rets.index).fillna(0.0)
    asset_r = pos * rets - COST * pos.diff().abs().fillna(0.0)
    w = (1 / vol).reindex(rets.columns)
    basket = (asset_r * w).mean(axis=1, skipna=True) / w.mean()
    return basket.dropna(), asset_r


def stats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 50 or r.std() == 0:
        return {"n_days": int(len(r))}
    eq = r.cumsum()
    return {"n_days": int(len(r)), "ann_ret_pct": round(r.mean() * 252 * 100, 2),
            "sharpe": round(r.mean() / r.std() * np.sqrt(252), 2),
            "max_dd_pct": round((eq.cummax() - eq).max() * 100, 1),
            "hit_years": f"{int((r.groupby(r.index.year).sum() > 0).sum())}/{r.index.year.nunique()}"}


def per_asset(asset_r: pd.DataFrame) -> pd.DataFrame:
    rows = {a: stats(asset_r[a]) for a in asset_r.columns}
    df = pd.DataFrame(rows).T
    df["gruppe"] = [next(g for g, xs in GROUPS.items() if a in xs) for a in df.index]
    return df


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["is", "oos", "tresor"], required=True)
    stage = ap.parse_args(argv).stage
    lk = Lock(STRATEGY)
    lk.register_split(*SPLIT)

    rets = universe_returns()
    labels = m.daily_labels(rets.index)
    rets = rets.loc[labels.index]
    rets_is = lk.is_only(rets)

    if stage == "is":
        if lk._load()["frozen"] is None and lk.trials == 0:
            lk.log_trials(len(LENSES), "Linsen joint/change/signs, Richtung = IS-Vorzeichen je Regime")
        res = {}
        for lens in LENSES:
            lab = labels.loc[rets_is.index, lens]
            dirs = directions(rets_is, lab)
            basket, _ = run(rets_is, lab, dirs, rets_is.std())
            res[lens] = stats(basket)
            print(f"IS {lens}: {res[lens]}")
        best = max(res, key=lambda k: res[k].get("sharpe") or -9)
        lab = labels.loc[rets_is.index, best]
        dirs = directions(rets_is, lab)
        basket, asset_r = run(rets_is, lab, dirs, rets_is.std())
        dsr = deflated_sharpe(float(basket.mean() / basket.std()), len(basket), lk.trials)
        h = lk.freeze({"lens": best, "directions": {k: {a: float(v) for a, v in row.items()}
                                                    for k, row in dirs.iterrows()},
                       "is_vol": {a: float(v) for a, v in rets_is.std().items()}, "cost": COST})
        print(f"\nGewinner (IS-Sharpe): {best} · DSR {dsr:.3f} · eingefroren {h[:12]}")
        print("\nRichtungen je Regime (IS):\n" + dirs.replace({1.0: "long", -1.0: "short", 0.0: "–"}).T.to_string())
        print("\nJe Asset (IS):\n" + per_asset(asset_r).to_string())
        return 0

    st = lk._load()
    cfg = st["frozen"]
    if cfg is None:
        raise SystemExit("erst --stage is")
    lens = cfg["config"]["lens"]
    dirs = pd.DataFrame(cfg["config"]["directions"]).T
    vol = pd.Series(cfg["config"]["is_vol"])
    lk.unseal(stage, cfg["hash"])
    seg = lk.stage_slice(rets, stage)
    basket, asset_r = run(seg, labels.loc[seg.index, lens], dirs, vol)
    print(f"{stage.upper()} ({lens}): {stats(basket)}")
    pa = per_asset(asset_r)
    print("\nJe Asset:\n" + pa.to_string())
    print("\nJe Gruppe (Mittel Sharpe):\n" + pa.groupby("gruppe").sharpe.apply(
        lambda s: round(pd.to_numeric(s, errors="coerce").mean(), 2)).to_string())
    OUT.mkdir(parents=True, exist_ok=True)
    pa.to_csv(OUT / f"direction_{stage}.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
