import argparse
import sys

from fusion_lab.agent_forward import ledger


def main() -> int:
    ap = argparse.ArgumentParser(prog="python -m fusion_lab.agent_forward")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="Tageslauf (Abrechnung + Entscheide + Summary)")
    r.add_argument("--tickers", nargs="+", help="nur diese Titel (Test)")
    r.add_argument("--force", action="store_true", help="Uhrzeit-Pruefung ueberspringen (Handelstag bleibt Pflicht)")
    r.add_argument("--datum", help="nur Test: frueherer Handelstag (historischer Modus, zaehlt als Probe)")
    sub.add_parser("summary", help="nur summary.json neu rechnen")
    a = ap.parse_args()
    if a.cmd == "summary":
        s = ledger.write_summary()
        print(f"summary.json: Stand {s['stand']}, {sum(q['n'] for q in s['quellen'].values())} Entscheide")
        return 0
    from fusion_lab.agent_forward.run import run
    return run(a.tickers, a.force, a.datum)


if __name__ == "__main__":
    sys.exit(main())
