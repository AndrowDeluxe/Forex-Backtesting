Consolidated monthly version of the two weekly reports (see
`scripts/reports/weekly_report_prompt.md` for full context on data sources -
same rules apply: prefer each bot's own bridge folder/sqlite/MT5 history
over this repo's diagnostic logs, flag disagreements rather than hiding them,
summarize trades/winrate/PnL per bot - never list individual trades).

This runs as a follow-on to the weekly report, on the last Sunday before the
month rolls over. Read all of this month's files in
`knowledge/reports/weekly/` (the ones falling inside the current calendar
month) and consolidate - do not redo the underlying data-gathering from
scratch where the weekly reports already captured it correctly, but DO
pull a fresh month-to-date PnL figure per bot directly from each bridge's
sqlite/MT5 history rather than just summing the weekly numbers (rounding/
week-boundary effects compound - a fresh month-start-to-month-end read is
more reliable than adding up 4-5 weekly deltas).

Both reports together are called **"Monthly Checkup"** (same branding as
the weekly "Weekly Checkup" reports, just monthly scope).

## Report 1: Monthly Checkup - Performance

File: `knowledge/reports/monthly/<YYYY-MM>_performance.md`. Title the
document itself "Monthly Checkup - Performance - <Month> <YYYY>".

Same structure as the weekly performance report, but:
- Trades/winrate/PnL figures are for the full month (fresh pull, not summed
  weeklies - see above).
- Add a short trend line per bot: did performance improve, worsen, or stay
  flat across the weeks of this month (reference the weekly files briefly).
- Add a portfolio-vs-individual-accounts note if the Portfolio Bot (FK
  Instant Funding / `fk_instant_funding/paper_bot.py`) has real trade
  history this month: how did the combined portfolio's risk-adjusted
  performance (drawdown, consistency) compare to what the same capital
  would have looked like split across individual per-strategy accounts?
  (See `portfolio_construction/results/fk_instant_funding_final.json` for
  the existing backtested comparison as a reference point - CAGR/Sharpe/
  MaxDD/Calmar for portfolio vs. each leg standalone.)

## Report 2: Monthly Checkup - Education

File: `knowledge/reports/monthly/<YYYY-MM>_education.md`. Title the
document itself "Monthly Checkup - Education - <Month> <YYYY>".

Read all of the month's weekly education reports first
(`knowledge/reports/weekly/KW*_education.md`) - the monthly report is a
synthesis that adds to them, not a concatenation. Depth follows the weekly
rules (Nutzerwunsch 2026-09-30: Education-Teil ausfuehrlicher). Structure:

1. **Der Monat in einem Absatz**: main themes across the weeks and how
   the focus shifted from week to week.
2. **Die 3-5 wichtigsten Erkenntnisse des Monats**: each as a sub-block
   with Befund / Mechanismus / Wie es aufgefallen ist / Lehre (same four
   parts as the weekly "Main Erkenntnisse", ~150-300 words each). Choose by
   lasting weight, not by recency; where several weekly learnings are
   really the same pattern (e.g. several "Entry-Lag frisst den Edge"
   cases), merge them into one learning and say so - that pattern
   recognition is the monthly report's main added value.
3. **Muster ueber die Wochen**: recurring root causes or mistakes
   (e.g. same class of bug in several bridges, same kind of paper edge
   decaying) - name the pattern, list the instances, and state whether a
   structural fix exists or is still open.
4. **Research-Bilanz**: table of every paper/strategy candidate touched
   this month - Quelle, Behauptung, unser Ergebnis (deciding number),
   Status. Below it, 2-3 sentences on what the month taught about which
   KINDS of edges survive our tests and which don't.
5. **Vertiefung des Monats**: one concept explained in more depth than a
   weekly box (~300-500 words), ideally one that tied several of the
   month's findings together.
6. **Netto-Bilanz**: improvements vs. regressions of the month.
7. **Offen in den naechsten Monat**: open items, ordered by importance,
   each with the concrete next step.

## Report 3: PDF (both parts combined, styled)

Same design/process as the weekly PDF (see
`scripts/reports/weekly_report_prompt.md`, "Report 3" section, for the
full instructions and the exact tested Edge command - reuse it verbatim,
just swap the file names):

- Reuse the `<style>` block from
  `scripts/reports/templates/example_weekly_checkup.html` unchanged.
- Write `knowledge/reports/monthly/<YYYY-MM>_checkup.html`.
- Render to PDF at
  `C:\Users\andre\Documents\Trading Reports\<YYYY-MM>_checkup.pdf` (same
  dedicated folder as the weekly PDFs, not committed to git; the `.html`
  source is committed).
- No email sending (user chose Telegram instead, same note as the weekly report).

## Report 4: Send the PDF via Telegram

Same as the weekly report's "Report 4" section - reuse
`scripts/reports/telegram_notify.py::send_telegram_document()` verbatim,
just point it at `<YYYY-MM>_checkup.pdf` and caption it "Monthly Checkup -
<Month> <YYYY>" plus the single most important open item.

## After writing all files

`git add knowledge/reports/ && git commit -m "Monthly Checkup: <YYYY-MM>"`
(local commit only, can be combined with the weekly commit into one if run
together - do NOT push).
