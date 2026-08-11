"""Parses raw_tables.py (Appendix Tables 4-9 from Yildirim SSRN 6353258) into
per-bank date lists, cross-checks each year's parsed count against the
declared N, and writes the result to data_cache/bond_yield_indicator/
cb_calendar_paper.csv. Run once; output is committed as a static file (same
convention as the rest of this repo's cached external data)."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from raw_tables import TABLES

MONTH_NUM = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
)}

ROW_RE = re.compile(r"^(\d{4})\s+(\d+)\s+(.*)$")
DATE_RE = re.compile(r"(\d{1,2})-([A-Za-z]{3})")


def parse_table(name: str, text: str) -> list[tuple[str, str]]:
    """Returns list of (bank, iso_date) tuples, printing a mismatch warning
    per row where the parsed date count differs from the table's declared N
    (a genuine transcription-integrity check, not a formality)."""
    out = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = ROW_RE.match(line)
        if not m:
            print(f"  [{name}] UNPARSEABLE ROW: {line!r}")
            continue
        year, n_declared, rest = m.group(1), int(m.group(2)), m.group(3)
        dates = DATE_RE.findall(rest)
        if len(dates) != n_declared:
            print(f"  [{name}] {year}: declared N={n_declared} but parsed {len(dates)} dates -> {dates}")
        for day, mon in dates:
            iso = f"{year}-{MONTH_NUM[mon]:02d}-{int(day):02d}"
            out.append((name, iso))
    return out


def main():
    all_rows = []
    for name, text in TABLES.items():
        print(f"Parsing {name} ...")
        rows = parse_table(name, text)
        print(f"  {name}: {len(rows)} meeting dates, {rows[0][1]} .. {rows[-1][1]}")
        all_rows.extend(rows)

    out_dir = Path(__file__).resolve().parents[1] / "calendars"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "cb_calendar_paper.csv"
    with out_path.open("w", encoding="utf-8") as f:
        f.write("bank,date\n")
        for bank, iso in all_rows:
            f.write(f"{bank},{iso}\n")
    print(f"\nWrote {len(all_rows)} rows -> {out_path}")


if __name__ == "__main__":
    main()
