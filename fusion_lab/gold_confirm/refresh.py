"""Taeglicher Refresh fuer das CTNL-Makro-Gate: FRED + yfinance neu laden, Score-Frame neu bauen.

Aufruf: python -m fusion_lab.gold_confirm.refresh   (Scheduled Task, werktags frueh morgens)
Schreibt fusion_lab/data/gold_confirm/score_frame.parquet, das gold_smc_htf_ltf/macro_gate.py liest.
"""
from __future__ import annotations

import sys

from fusion_lab.gold_confirm import data
from fusion_lab.gold_confirm.score import build

FRAME = data.DATA_DIR / "score_frame.parquet"


def main() -> int:
    data.main(["fred", "yf", "spot"])
    f = build()
    tmp = FRAME.with_suffix(".tmp.parquet")
    f.to_parquet(tmp)
    tmp.replace(FRAME)  # atomar: das Gate liest nie eine halbe Datei
    m = f["MACRO"].dropna()
    print(f"score_frame bis {f.index.max():%Y-%m-%d}, MACRO {m.iloc[-1] * 100:.1f} (Stand {m.index[-1]:%Y-%m-%d})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
