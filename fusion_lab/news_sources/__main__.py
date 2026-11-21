from __future__ import annotations

import sys

import pandas as pd

from fusion_lab.news_sources import collectors, pipeline, report
from fusion_lab.news_sources import config as C


def _status(quellen: dict) -> None:
    for q, s in quellen.items():
        print(f"  {q:18s} {s['status']:20s} {s.get('eintraege', ''):>4} {s['grund']}")


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "collect"
    if cmd == "collect":
        raw = collectors.collect(list(C.UNIVERSE), daily="--daily" in argv)
        _status({q: {**r, "eintraege": len(r["items"]) + len(r["werte"])} for q, r in raw.items()})
    elif cmd in ("snapshot", "record"):
        if cmd == "record":
            snap, n = pipeline.record(daily=True)
            print(f"Ledger: {n} neue Zeilen")
        else:
            syms = next((a.split("=", 1)[1].split(",") for a in argv if a.startswith("--symbols=")), None)
            snap = pipeline.snapshot(symbols=syms, daily="--daily" in argv)
        _status(snap["quellen"])
        cl = snap["claude"]
        print(f"  claude             {cl['status']:20s} {len(cl.get('ergebnis') or {}):>4} {cl['grund']}")
        for w in cl.get("warnungen", [])[:10]:
            print("    Warnung:", w)
    elif cmd == "report":
        ev, av = report.report()
        pd.set_option("display.width", 200)
        print("Verfuegbarkeit je Quelle:\n", av.to_string() if len(av) else "(noch keine Laeufe)")
        print("\nAuswertung (vorsprung > 0 = besser als die Marktrichtung):\n",
              ev.to_string(index=False) if len(ev) else "(noch keine faelligen Horizonte)")
    else:
        print(__doc__ or "", "unbekannter Befehl:", cmd)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
