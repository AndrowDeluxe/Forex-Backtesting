"""Fact Sheet erzeugen.

    python -m fusion_lab.macro_agent                     # Stand heute
    python -m fusion_lab.macro_agent --as-of 2026-11-09  # Stand eines vergangenen Tages
    python -m fusion_lab.macro_agent --notion            # zusaetzlich nach Notion
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from . import fact_sheet, render


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", help="Stand (YYYY-MM-DD), Standard heute")
    parser.add_argument("--notion", action="store_true", help="Seite im Trading Fusion Cockpit aktualisieren")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sheet = fact_sheet.build(pd.Timestamp(args.as_of) if args.as_of else None)
    j, m = fact_sheet.write(sheet, render.markdown(sheet))
    print(f"Fact Sheet {sheet['stand']}: Zustand {sheet['zustand']['state']}, {len(sheet['register'])} Zahlen\n{j}\n{m}")
    if args.notion:
        from fusion_lab.notion.sync_fact_sheet import sync
        print(sync(sheet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
