"""One-off fetch of FOMC meeting/announcement dates 2016-2026 from the Fed's
own historical-materials pages (2016-2020) and current calendars page
(2021-2026), parsed from HTML. Run once; output committed as a static CSV
(data_cache/bond_yield_indicator/fomc_calendar.csv) so the backtest doesn't
depend on live scraping (page format can change) and stays reproducible.
Announcement date = last day of each 2-day meeting (the day the decision is
released). 2020 COVID emergency actions (March 3, March 15) are included as
real rate-decision dates; the cancelled March 17-18 regular meeting (rolled
into the March 15 emergency action) is excluded."""

import csv
import datetime
import re
import urllib.request
from pathlib import Path

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
MNUM = {m: i + 1 for i, m in enumerate(MONTHS)}
ABBR = {m[:3]: m for m in MONTHS}
NAME = {**{m: m for m in MONTHS}, **ABBR}
NAME_ALT = "|".join(list(MONTHS) + list(ABBR))

PAT_CROSS = re.compile(rf"^({NAME_ALT})/({NAME_ALT}) (\d{{1,2}})-(\d{{1,2}}) Meeting - (\d{{4}})$")
PAT_RANGE = re.compile(rf"^({NAME_ALT}) (\d{{1,2}})-(\d{{1,2}}) Meeting - (\d{{4}})$")
PAT_SINGLE = re.compile(rf"^({NAME_ALT}) (\d{{1,2}}) (?:\(unscheduled\) )?Meeting - (\d{{4}})$")
PAT_FULL_LOOKAHEAD = re.compile(
    rf"({NAME_ALT}) (\d{{1,2}})(?:[-–](?:({NAME_ALT}) )?(\d{{1,2}}))?\*?\s*"
    rf"(?=Statement|Press Conference|{NAME_ALT}|\Z)"
)
PAT_ABBR_INLINE = re.compile(rf"({'|'.join(ABBR)})/({'|'.join(ABBR)}) (\d{{1,2}})-(\d{{1,2}})")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="ignore")


def parse_heading(h: str):
    h = h.strip()
    if "(cancelled)" in h:
        return None  # rolled into an unscheduled action on a different date
    m = PAT_CROSS.match(h)
    if m:
        _, m2, _, d2, year = m.groups()
        return datetime.date(int(year), MNUM[NAME[m2]], int(d2))
    m = PAT_RANGE.match(h)
    if m:
        m1, _, d2, year = m.groups()
        return datetime.date(int(year), MNUM[NAME[m1]], int(d2))
    m = PAT_SINGLE.match(h)
    if m:
        m1, d1, year = m.groups()
        return datetime.date(int(year), MNUM[NAME[m1]], int(d1))
    return None


def fetch_historical_years(years) -> set[datetime.date]:
    dates = set()
    for year in years:
        html = fetch(f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm")
        headings = re.findall(r'panel-heading--shaded">([^<]*)</h5>', html)
        for h in headings:
            if "Meeting" in h:
                d = parse_heading(h)
                if d:
                    dates.add(d)
    return dates


def fetch_calendar_page(year_min: int, year_max: int) -> set[datetime.date]:
    html = fetch("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    year_blocks = re.split(r"(\d{4}) FOMC Meetings", text)
    dates = set()
    for i in range(1, len(year_blocks), 2):
        year = int(year_blocks[i])
        if not (year_min <= year <= year_max):
            continue
        content = year_blocks[i + 1].split("Future Year")[0]
        for m in PAT_ABBR_INLINE.finditer(content):
            _, m2, _, d2 = m.groups()
            dates.add(datetime.date(year, MNUM[ABBR[m2]], int(d2)))
        masked = PAT_ABBR_INLINE.sub(lambda m: " " * len(m.group(0)), content)
        for m in PAT_FULL_LOOKAHEAD.finditer(masked):
            m1, d1, m2, d2 = m.groups()
            end_month = m2 if m2 else m1
            end_day = int(d2) if d2 else int(d1)
            try:
                dates.add(datetime.date(year, MNUM[end_month], end_day))
            except ValueError:
                pass
    return dates


def main():
    dates = fetch_historical_years(range(2016, 2021))
    dates |= fetch_calendar_page(2021, 2026)
    dates = sorted(dates)

    out_dir = Path(__file__).resolve().parents[1] / "calendars"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "fomc_calendar.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bank", "date"])
        for d in dates:
            w.writerow(["FOMC", d.isoformat()])

    by_year = {}
    for d in dates:
        by_year.setdefault(d.year, []).append(d)
    for y in sorted(by_year):
        print(y, len(by_year[y]), by_year[y])
    print(f"\nWrote {len(dates)} rows -> {out_path}")


if __name__ == "__main__":
    main()
