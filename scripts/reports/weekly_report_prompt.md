You are running unattended (Windows Task Scheduler, every Sunday evening, no
human present to answer questions). Produce two markdown reports for the
past trading week and commit them locally. Do not ask questions - if
something is ambiguous or a data source is unavailable, write down the
uncertainty in the report itself (as the user's mentor-style journal does:
flag it, don't silently guess) and move on.

Working directory: C:\Users\andre\Forex-Backtesting (this repo). Read
MEMORY.md and the files it links at
C:\Users\andre\.claude\projects\c--Users-andre-Forex-Backtesting\memory\ first
- they contain the full history of bugs found/fixed in this bot fleet and
which data sources are trustworthy vs. not. Do not repeat work already
described there; build on it.

## Critical lesson from 2026-08-26/27 (READ THIS FIRST)

The REAL, authoritative live-trading data for most bots does NOT live in
this git repo. Each bot that actually places MT5 orders has its own
standalone folder directly under `C:\Users\andre\<BotName>-Bridge\` (or
similar, e.g. `TrendPullback-Bot\FK1\`, `TrendPullback-Bot\FK2\`) - NOT
a git repo, outside `Forex-Backtesting\`. Known bridge folders as of
2026-08-27 (check for new ones too - list `C:\Users\andre\` for
`*-Bridge`/`*-Bot` folders you don't recognize):
- `C:\Users\andre\BTC-EMA-Cross-Bridge\` (login 15514, shared with GoldASB)
- `C:\Users\andre\CLS-Practical-Bridge\` (login 5053949028, own dedicated
  terminal at `C:\Users\andre\MT5-Terminals\MT5 Terminal - CLSPractical\`)
- `C:\Users\andre\GoldASB-MT5-Bridge\` (accounts: goldasb_beyondiq login
  15514 shared terminal, goldasb_demo - check if still active, it went
  quiet after 2026-08-06)
- `C:\Users\andre\CTNL-Edge-MT5-Bridge\` (login 16054, own dedicated
  terminal `MT5-Terminals\MT5 Terminal - GoldFKBot\`, started 2026-08-20)
- `C:\Users\andre\TrendPullback-Bot\FK1\` and `\FK2\` (own dedicated
  terminals `MT5-Terminals\MT5 Terminal - FK1\`/`FK2\`, login 111188068 etc.)
- `C:\Users\andre\OU-Modell-MT5-Bridge\` (3 accounts: Konto1 TTP, Konto2 TTP
  Demo, Konto3 Tickmill - Konto1/Konto3 look like real/live capital, not
  just demo challenges, based on account name/server - found missing from
  this known-bridges list during the 2026-08-27 first run; always do a
  fresh `Get-ChildItem C:\Users\andre\ -Directory` sweep for `*-Bridge`/
  `*-Bot` folders each time rather than trusting only this list, since it
  has already been proven incomplete once)
- `C:\Users\andre\Forex-Backtesting\fk_instant_funding\paper_bot.py` (the
  "Portfolio Bot", 5 legs sharing one virtual account - check if it has
  been switched from paper-simulation to real execution; as of 2026-08-26
  it was still pure simulation, re-running each leg's own signal engine,
  NOT a real MT5 connection)

Each bridge folder has `logs/` (per-run text logs) and `state/*.sqlite3`
(tables like `executed_signals`, `daily_baseline`/`weekly_baseline`,
`positions`, `heartbeats` - schemas vary per bot, inspect with
`sqlite3`/python before assuming a schema). THIS sqlite/log data is the
ground truth for what actually happened. The repo's own `*_logs/`
folders (e.g. `gold_asb_logs/`, `cls_practical_logs/`, `btc_ema_cross_logs/`)
are mostly separate diagnostic/simulation scripts (e.g.
`cls_practical/live_scan.py::scan_today()`) that can DISAGREE with the
real bridge - confirmed disagreement found for BTC EMA Cross (repo log
showed +3%/1 trade that never really happened; real account was flat,
zero real fills). Always prefer the bridge's own sqlite/logs; if you
only have the repo diagnostic for some bot, say so explicitly in the report
rather than presenting it as confirmed real performance.

For MT5-connected bots, you may also connect read-only via the
`MetaTrader5` python package (`mt5.initialize(path=..., login=..., ...)`,
credentials are in each bridge's own `config.py`) to pull
`account_info()`/`history_deals_get()` for the past week directly from the
broker - this is the most authoritative source when available and worth
doing for a weekly figure, not just reading local state files. Only ever
READ (account_info, history_deals_get, positions_get) - never place,
modify or cancel any order from this report-generation task.

Both reports together are called **"Weekly Checkup"** - use the German
calendar-week notation "KW<n>" (ISO week number, e.g. "KW35"), not the
ISO "2026-W35" form, in both filenames and document titles.

## Report 1: Weekly Checkup - Performance

File: `knowledge/reports/weekly/KW<n>_<year>_performance.md` (e.g.
`KW35_2026_performance.md`). Compute the ISO week number for "today"; if
today is Sunday, this report covers the Monday-Sunday week ending today.
Title the document itself "Weekly Checkup - Performance - KW<n>/<year>".

Structure (mirrors the user's own weekly trading journal - see
`knowledge/reports/_templates/` if present for the exact source images/
text; otherwise use this structure):

1. **Wochenkontext**: one paragraph - which bots/legs were live this week,
   any that started, stopped, or had config changes (check git log in this
   repo for the week, and check each bridge folder's file mtimes).
2. **Risk-Management-Compliance**: for each active bot, did it respect its
   own configured risk limits (max risk/trade, daily/weekly drawdown caps,
   kill-switches)? Did any kill-switch or drawdown halt trigger this week?
   Flag violations clearly - this is the single most important compliance
   check in the user's template.
3. **Was hat gut / nicht gut funktioniert**: short per-bot bullet, not
   a full trade-by-trade breakdown.
4. **Trades, Winrate, Gewinn ($ and %) - SUMMARY ONLY**: one line per bot/
   leg: number of trades, win rate, $ and % PnL for the week. The user
   explicitly does NOT want individual trades listed out - aggregate only.
   Also give the combined total across all active bots, and the Portfolio
   Bot's own number separately if it has gone live by the time you run this.
5. **Auffälligkeiten / offene Punkte**: anything that looks wrong (a bot
   silently not running, a data source you couldn't trust, a discrepancy
   between bridge data and repo diagnostic) - flag it the way memory
   already models (see the CLS date-bug and CTNL false-alarm entries for
   the tone/rigor expected here). Don't silently smooth over gaps.

## Report 2: Weekly Checkup - Education

File: `knowledge/reports/weekly/KW<n>_<year>_education.md`. Title the
document itself "Weekly Checkup - Education - KW<n>/<year>".

Structure (adapted from the user's mentor-style reflection journal):

1. **Was stand die Woche an / Hauptfokus**: derive from `git log --since=
   "7 days ago" --oneline` in this repo (and check for related work in the
   knowledge-memory files), summarize what was actually worked on.
2. **Aktive Zeiten**: rough sense of when work happened this week (commit
   timestamps, bridge log timestamps) - doesn't need to be precise, just
   a "mostly evenings/weekends" style observation.
3. **Meine Main Erkenntnisse**: the week's key learnings - new bugs found,
   new architectural decisions, anything that changed how the user should
   think about the system. Pull from new/updated files in
   C:\Users\andre\.claude\projects\c--Users-andre-Forex-Backtesting\memory\
   this week plus new `knowledge/` docs.
4. **Verbesserungen**: bugs fixed, infra improved, new validated strategies/
   features shipped this week.
5. **Verschlechterungen / offene Probleme**: anything newly broken,
   regressed, or found-but-not-yet-fixed this week.
6. **Optimierungsmöglichkeiten**: what would be worth tackling next,
   based on what surfaced this week.

## Report 3: PDF (both parts combined, styled)

The user has approved a specific visual design for this ("ledger" look -
paper background, Spectral serif headings, IBM Plex Sans body, IBM Plex
Mono tabular numbers, teal accent, brick-red left-border callouts for
flagged issues). Do NOT redesign this from scratch - reuse it exactly:

1. Copy the entire `<style>` block from
   `scripts/reports/templates/example_weekly_checkup.html` verbatim (it's
   self-contained: Google Fonts import + full light/dark CSS). Reuse the
   same class names/structure it demonstrates (`.sheet`, `.part`,
   `section.block`, `h3.sec .num`, `.flag`, `.chip`, the trades table
   structure, the `.bars` weekday-activity chart) - that file is a real,
   previously-approved example for a past week (KW34), not a placeholder
   to fill in; write this week's actual content in the same structure.
2. Write the combined HTML (masthead + Part I Performance + Part II
   Education, same content as the two markdown files above, same
   "summarize trades, don't list them individually" rule) to
   `knowledge/reports/weekly/KW<n>_<year>_checkup.html`.
3. Render it to PDF with headless Edge - use this EXACT invocation (a
   different flag combination silently fails with "Multiple targets are
   not supported in headless mode", already debugged once, don't
   rediscover it):
   ```powershell
   $edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
   $html = "C:\Users\andre\Forex-Backtesting\knowledge\reports\weekly\KW<n>_<year>_checkup.html"
   $pdf  = "C:\Users\andre\Documents\Trading Reports\KW<n>_<year>_checkup.pdf"
   $userDataDir = "$env:TEMP\edge-headless-pdf-$(Get-Random)"   # MUST be a fresh/unique dir every run - see note below
   $fileUrl = "file:///" + ($html -replace '\\','/')
   & $edge --headless=new --disable-gpu "--user-data-dir=$userDataDir" "--print-to-pdf=$pdf" --no-pdf-header-footer $fileUrl
   ```
   Run this via the Bash tool (it can invoke `powershell.exe -Command "..."`
   or you may already be in a PowerShell-capable shell - check what's
   available). **`--user-data-dir` MUST be unique per run** (the
   `-$(Get-Random)` suffix above, or a timestamp) - reusing the same fixed
   directory across runs was tested 2026-08-27 and intermittently fails
   silently (exit code 0, no PDF written, stale profile/lock state from
   the previous run) - already debugged once, don't reintroduce it.
   Confirm the PDF file exists and is a non-trivial size (100KB+)
   afterward - don't just trust exit code 0; if it's missing, retry once
   with a brand-new random user-data-dir before giving up and flagging it
   in the report instead.
4. The PDF lives ONLY in `C:\Users\andre\Documents\Trading Reports\` (the
   user's chosen folder, 2026-08-27 decision) - it is NOT committed to
   git. The `.html` source IS committed (part of `knowledge/reports/`,
   see below) so it stays git-versioned even though the PDF itself isn't.
5. No email sending (deliberately not set up, user chose Telegram instead
   on 2026-08-27) - if this prompt is ever updated to add email,
   credentials must be read from a local, gitignored file - never
   hardcode them here.

## Report 4: Send the PDF via Telegram

Uses the same shared bot/chat as the other bots (CLS-Practical-Bridge,
OU-Modell-MT5-Bridge, etc.) - user's explicit choice 2026-08-27 ("in den
Bot mit einbauen" rather than a new bot). From this repo's root (or
`cd scripts/reports` first, since the config import is relative to that
directory - see `telegram_notify.py`'s own import):

```python
import sys
sys.path.insert(0, r"C:\Users\andre\Forex-Backtesting\scripts\reports")
from telegram_notify import send_telegram_document, SIGNATURE

ok = send_telegram_document(
    r"C:\Users\andre\Documents\Trading Reports\KW<n>_<year>_checkup.pdf",
    caption=f"{SIGNATURE}\n\nWeekly Checkup - KW<n>/<year>\n<one-line headline of the single most important flag from Report 1, section 5 - e.g. the most severe open issue - so the Telegram notification itself is useful even before opening the PDF>",
)
```

If `scripts/reports/telegram_config.py` doesn't exist (gitignored, must be
created once locally - see `telegram_config.example.py`), `send_telegram_
document()` returns `False` without erroring - Telegram is optional, note
this in the report if it happens but don't treat it as a failure of the
whole run. Never let a Telegram error abort report generation - it must
already be caught inside `telegram_notify.py`, but treat this step as
best-effort regardless.

## After writing all files

`git add knowledge/reports/ && git commit -m "Weekly Checkup: KW<n>/<year>"`
in this repo (local commit only - do NOT push). If it is also the last
Sunday before the month rolls over (i.e. adding 7 days to today crosses
into a new month), ALSO produce the two monthly reports per
`scripts/reports/monthly_report_prompt.md` before committing (one combined
commit is fine).
