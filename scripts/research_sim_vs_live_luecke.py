"""Luecke Simulation vs. echte Konten seit Livegang -- Bein fuer Bein.

Nutzerauftrag 2026-10-04 (nach der Gegenprobe in
research_challenge_ek_gewichtung_mc_wf.py: Sim TTP +0,6 / IQ +1,4 / EK +1,3 %
gegen real -0,65 / -2,5 / -18,2 %). Nutzer-Hypothese: die Luecke kommt vom
vielen Umbau, nicht von einer falschen Strategie-Annahme.

REAL: geschlossene Deals aus den vorhandenen MT5-Abzuegen
(scripts/reports/mt5_2026-09_month.json + mt5_2026-W40.json, dedupliziert ueber
das Deal-Ticket), Zuordnung zum Bein wie soll_ist.py (EK ueber Magic, Funded
ueber die Tickets im bridge_state). Liest keine Terminals.

SIM: die Trade-Listen aus research_live_legs.py (HEUTIGER Code) im selben
Fenster, Groesse = Risiko-Anteil x Startequity (ein Monat -> ohne
Compounding), Mindestlot wie im Optimierer. Gewichte = was im Fenster live
lief (TTP 1/6-Formel, IQ 1/3, EK heutige Werte -- EK wurde im Fenster zweimal
umkalibriert, 10.09. und 23.09.).

Zerlegung je Bein in vier Topfe:
  nur_live     Bein lief live, die heutige Sim hat es nicht (abgeschaltet)
  nur_sim      Sim handelt, live kam nichts an (nie platziert)
  beide        Differenz bei Beinen, die auf beiden Seiten handeln
  fremd        Deals ohne Bein-Zuordnung (Hand-Trades, verlorener State)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "reports"))
import research_challenge_ek_gewichtung_mc_wf as M  # noqa: E402
import soll_ist as SI  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PULLS = [REPO / "scripts" / "reports" / "mt5_2026-09_month.json", REPO / "scripts" / "reports" / "mt5_2026-W40.json"]
KONTEN = {  # Konto -> (Label im MT5-Abzug, Startdatum, Startequity, Bridge-Key fuer soll_ist)
    "ttp": ("Funded / TTP Challenge (ttp)", "2026-09-01", 99_872.0, "funded"),
    "iq": ("Funded / IQ Challenge (iqmarkets)", "2026-09-01", 100_000.0, "funded"),
    "ek": ("EK-Portfolio-Bridge / Tickmill", "2026-08-29", 3_468.0, "ek"),
}
END = "2026-10-03"
OUT = REPO / "knowledge" / "_data" / "sim_vs_live_luecke.json"


def real_deals(label: str) -> pd.DataFrame:
    rows = {}
    for p in PULLS:
        d = json.loads(p.read_text(encoding="utf-8"))
        rec = d["accounts"].get(label, {})
        for x in rec.get("deals", []):
            rows[x.get("ticket")] = x
    df = pd.DataFrame(list(rows.values()))
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["time"], unit="s", errors="coerce") if np.issubdtype(df["time"].dtype, np.number) \
        else pd.to_datetime(df["time"], errors="coerce")
    return df


def real_per_leg(acc: str) -> tuple[pd.DataFrame, dict]:
    label, start, _, bkey = KONTEN[acc]
    df = real_deals(label)
    spec = SI.bridge_specs()[bkey]
    by_magic = SI._ek_leg_by_magic() if spec.uses_magic else {}
    by_ticket = {} if spec.uses_magic else SI._ticket_to_leg(spec)
    closes = df[(df["entry"] == 1) & (df["time"] >= pd.Timestamp(start)) & (df["time"] < pd.Timestamp(END))].copy()
    closes["pnl"] = closes[["profit", "swap", "commission", "fee"]].fillna(0).sum(axis=1)
    # Kommission der Eroeffnungs-Deals gehoert dazu (TTP/IQ buchen sie beim Entry)
    opens = df[(df["entry"] == 0) & (df["time"] >= pd.Timestamp(start)) & (df["time"] < pd.Timestamp(END))]
    open_comm = opens.groupby("position_id")["commission"].sum() if "commission" in opens else pd.Series(dtype=float)

    def leg_of(x):
        if spec.uses_magic:
            return by_magic.get(int(x.get("magic") or 0))
        leg = by_ticket.get(int(x.get("position_id") or 0))
        if leg is None:
            c = str(x.get("comment") or "")
            for cand in set(by_ticket.values()):
                if cand and cand in c:
                    return cand
        return leg

    closes["leg"] = closes.apply(leg_of, axis=1).fillna("FREMD")
    closes["pnl"] += closes["position_id"].map(open_comm).fillna(0.0)
    per = closes.groupby("leg").agg(pos=("position_id", "nunique"), pnl=("pnl", "sum"),
                                     swap=("swap", "sum")).round(2)
    meta = {"deals": int(len(closes)), "summe": round(float(closes["pnl"].sum()), 2),
            "abzug_bis": max(json.loads(p.read_text(encoding="utf-8"))["to"] for p in PULLS)}
    return per, meta


def sim_per_leg(acc: str) -> pd.DataFrame:
    _, start, eq0, _ = KONTEN[acc]
    a = M.ACCOUNTS[acc]
    t = M.load(acc)
    t = t[(t["entry_time"] >= pd.Timestamp(start)) & (t["exit_time"] < pd.Timestamp(END))].copy()
    ml = t["stop_px"].astype(float) * t["unit_usd"].astype(float) * a["ccy"] / eq0
    target = t["leg"].map(a["current"]).clip(upper=a["pos_cap"])
    lots = np.floor(target / ml.replace(0, np.nan) + 1e-9)
    risk = np.where(ml <= 0, target, np.where(lots >= 1, lots * ml, np.where(ml <= a["pos_cap"], ml, 0.0)))
    t["pnl"] = risk * eq0 * t["r"]
    t["leg"] = t["leg"].str.replace(r"^orb_.*", "orb", regex=True)
    return t.groupby("leg").agg(pos=("r", "size"), pnl=("pnl", "sum"), sum_r=("r", "sum")).round(2)


def main() -> None:
    result = {}
    for acc in KONTEN:
        real, meta = real_per_leg(acc)
        real.index = real.index.str.replace(r"^orb_.*", "orb", regex=True)
        real = real.groupby(level=0).sum()
        sim = sim_per_leg(acc)
        tab = real[["pos", "pnl", "swap"]].add_prefix("real_").join(sim[["pos", "pnl"]].add_prefix("sim_"), how="outer").fillna(0)
        tab["luecke"] = tab["real_pnl"] - tab["sim_pnl"]
        tab["topf"] = np.where(tab.index == "FREMD", "fremd",
                      np.where((tab["real_pos"] > 0) & (tab["sim_pos"] == 0), "nur_live",
                      np.where((tab["real_pos"] == 0) & (tab["sim_pos"] > 0), "nur_sim", "beide")))
        tab = tab.sort_values("luecke")
        toepfe = tab.groupby("topf")["luecke"].sum().round(2).to_dict()
        eq0 = KONTEN[acc][2]
        print(f"\n######## {acc.upper()}  (ab {KONTEN[acc][1]}, Start {eq0:,.0f})  real {meta['summe']:+,.2f}  "
              f"sim {sim['pnl'].sum():+,.2f}  Luecke {meta['summe'] - sim['pnl'].sum():+,.2f}  "
              f"({(meta['summe'] - sim['pnl'].sum()) / eq0 * 100:+.2f} %)")
        print(tab.round(2).to_string())
        print("  Toepfe:", toepfe)
        result[acc] = {"meta": meta, "sim_summe": round(float(sim["pnl"].sum()), 2),
                       "tabelle": tab.round(2).reset_index().to_dict(orient="records"), "toepfe": toepfe}
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {OUT}")


if __name__ == "__main__":
    main()
