"""Risiko-Budget je Idee: gleiches Risiko ueber Volatilitaet, Buendel-Check je Waehrung.

Idee = Paar mit |Score-Differenz| >= IDEA_MIN und ohne Veto in Richtung. Jede Idee traegt eine
Risikoeinheit; die Groesse relativ zum Median-Paar ist Median-Vol / eigene Vol. Netto-Exposure je
Waehrung = Summe der Einheiten (Basis +Richtung, Quote -Richtung); ueber CAP gilt das Buendel als
zu gross (Leitlinie „Buendeln statt zaehlen“, Vorschlag 1,5 Einheiten).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

IDEA_MIN = 0.75
CAP = 1.5
VOL_DAYS = 20


def realized_vol(close: pd.Series) -> float | None:
    r = np.log(close.dropna()).diff().dropna().iloc[-VOL_DAYS:]
    return None if len(r) < VOL_DAYS // 2 else float(r.std() * np.sqrt(252) * 100)


def ideas(pairs: dict[str, dict], vols: dict[str, float | None]) -> list[dict]:
    """pairs: Markt -> {"diff", "veto_long", "veto_short"}; nur FX-Paare mit Scorecard."""
    out = []
    for m, v in pairs.items():
        if v["diff"] is None or abs(v["diff"]) < IDEA_MIN:
            continue
        side = "long" if v["diff"] > 0 else "short"
        if v[f"veto_{side}"]:
            continue
        out.append({"markt": m, "seite": side, "diff": v["diff"], "vol_pct": None if vols.get(m) is None
                    else round(vols[m], 2)})
    known = [i["vol_pct"] for i in out if i["vol_pct"]]
    med = float(np.median(known)) if known else None
    for i in out:
        i["groesse_rel"] = round(med / i["vol_pct"], 2) if med and i["vol_pct"] else None
    return sorted(out, key=lambda i: -abs(i["diff"]))


def bundle(idea_list: list[dict]) -> dict:
    net: dict[str, float] = {}
    for i in idea_list:
        d = 1.0 if i["seite"] == "long" else -1.0
        base, quote = i["markt"][:3], i["markt"][3:6]
        net[base] = net.get(base, 0.0) + d
        net[quote] = net.get(quote, 0.0) - d
    over = {c: v for c, v in net.items() if abs(v) > CAP}
    return {"netto": {c: round(v, 2) for c, v in sorted(net.items(), key=lambda kv: -abs(kv[1]))},
            "ueber_deckel": over, "deckel": CAP,
            "haupttreiber": max(net, key=lambda c: abs(net[c])) if net else None}
