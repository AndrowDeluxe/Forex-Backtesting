"""Phase 1 Schritt 3: Backtest der SMH-Makro-Report-Ideen (Bewertungsmodus), v2.

v2 (16.10.2026): Nutzer-Stichprobe ergab, dass v1 Trade-Tabellen übersah und den
Status falsch definierte ("vorbereitet" statt "aktiv", wenn nur die technische
Bestätigung fehlte). Neu-Extraktion nach fusion_lab/data/macro_reports/extracted_v2/,
neue Status (aktiv/event/watch/bias/inaktiv), Rolle hedge, Sterne/Gates/Herkunft,
Variante D (Rücksetzer-Einstieg, Einstiegsstil des Nutzers). Der v1-Lock
"smh_macro_reports" wurde ohne einen einzigen Lauf ersetzt (Protokoll dort).

Overfitting-Sperre (Ausnahme begründet in knowledge/areas/overfitting-sperre.md):
  IS = gesamte Report-Historie 2025-08-03 .. 2026-10-07 (nichts optimiert, alle 5
  vorab festgelegten Varianten werden ausgewiesen), OOS = Forward-Reports
  2026-10-08 .. 2027-01-31, kein Tresor. Aufteilungen nach Sternen/Gates/Herkunft
  sind Auswertung, keine Auswahl -- eine daraus abgeleitete Regel ("nur 5 Sterne")
  gilt erst nach Bestätigung im Forward-Zeitraum.

    python -m scripts.research_smh_macro_reports
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from fusion_lab.macro_reports import backtest as bt  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402

STRATEGY = "smh_macro_reports_v2"
FOLDER = bt.DATA_DIR / "extracted_v2"
IS_START, IS_END, OOS_END = "2025-08-03", "2026-10-07", "2027-01-31"
VARIANTS = ["A1", "A2", "B", "C", "D"]
CONFIG = {
    "version": 2, "variants": VARIANTS, "selection": "A1/A2/B/D: status aktiv|bias, ohne hedge; C: Gen3 mit Aktivierungslevel",
    "atr_mult": bt.ATR_MULT, "default_target_r": bt.DEFAULT_TARGET_R, "time_exit_days": bt.TIME_EXIT_DAYS,
    "activation_window_days": bt.ACTIVATION_WINDOW_DAYS, "limit_atr": bt.LIMIT_ATR,
    "limit_valid_days": bt.LIMIT_VALID_DAYS, "cost_bps": bt.COST_BPS, "max_level_dist": bt.MAX_LEVEL_DIST,
    "stale_days": bt.STALE_DAYS, "entry": "first H1 open after Telegram post time (D: limit)",
    "stop_first_same_bar": True,
}


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END)
    if lk._load()["frozen"] is None:
        if lk.trials == 0:
            lk.log_trials(len(VARIANTS), "A1 Bias, A2 Main, B Level, C Aktivierung, D Rücksetzer -- vorab, v2")
        lk.freeze(CONFIG)
    return lk


def enrich(trades: pd.DataFrame, ideas: pd.DataFrame) -> pd.DataFrame:
    cols = ["msg_id", "instrument", "direction", "stars", "gates_met", "section", "event"]
    meta = ideas[cols].drop_duplicates(["msg_id", "instrument", "direction"])
    out = trades.merge(meta, on=["msg_id", "instrument", "direction"], how="left")
    out["klasse"] = out.instrument.map(bt.instrument_class)
    out["sterne"] = out.stars.map(lambda s: "ohne" if pd.isna(s) else f"{int(s)}")
    out["herkunft"] = out.section.fillna("?")
    return out


def main() -> int:
    lk = lock()
    ideas = bt.load_ideas(until=IS_END, folder=FOLDER)
    print(f"{ideas.msg_id.nunique()} Reports, {len(ideas)} Ideen; Status {ideas.status.value_counts().to_dict()}")
    px = bt.Prices("2025-06-01", "2026-10-31")

    summary, all_trades = {}, []
    for v in VARIANTS:
        tr = bt.run_variant(v, ideas, px, mode="v2")
        if tr.empty:
            summary[v] = {"n": 0}
            continue
        tr = enrich(tr, ideas)
        all_trades.append(tr)
        m = bt.metrics(tr)
        m["gross_mean_r"] = round(float(tr.r_gross.mean()), 3)
        m["perm_p"] = round(bt.permutation_p(tr), 4)
        sr = tr.r_net.mean() / tr.r_net.std(ddof=1) if len(tr) > 2 else np.nan
        m["deflated_sharpe"] = round(deflated_sharpe(float(sr), len(tr), lk.trials), 3) if np.isfinite(sr) else None
        summary[v] = m
        print(f"\n== {v}: {m}")
        for by in ("generation", "sterne", "gates_met", "herkunft", "klasse", "role"):
            print(bt.breakdown(tr, by).to_string())
        if v == "A1":
            summary["MOM20_control"] = bt.metrics(bt.momentum_control(tr, px))
            print(f"\n-- Kontrolle 20-Tage-Momentum: {summary['MOM20_control']}")

    # Hedges beschreibend (kein Kandidat): wie A1 gehalten
    hedges = ideas[(ideas.role == "hedge") & ideas.status.isin(bt.UNCONDITIONAL)]
    if not hedges.empty:
        h = bt.run_variant("A1", hedges.assign(role="secondary"), px, mode="v2")
        summary["hedges_described"] = bt.metrics(h) if not h.empty else {"n": 0}
        print(f"\n-- Hedges (beschreibend): {summary['hedges_described']}")

    trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    bt.save(trades, "trades_v2.csv")
    summary["missing_instruments"] = sorted(px.missing)
    summary["trials"] = lk.trials
    print(f"\nFehlende Kursdaten: {sorted(px.missing)}")
    print(f"-> {bt.dump_json(summary, 'summary_v2.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
