# Dashboard

**Stand: 2026-09-06** _(wird bei jeder Session von Claude auf das aktuelle
Datum nachgeführt — "Zuletzt geprüft" in der Statustabelle unten kann davon
abweichen und älter sein, siehe `CLAUDE.md` Punkt 4)._

Die tägliche Cockpit-Ansicht — hier reinschauen, nicht in Task Scheduler,
config.py-Dateien oder Chat-Verläufe wühlen. Funktioniert in jedem Editor,
kein Obsidian nötig. Wird von Claude bei jeder relevanten Änderung
nachgeführt (siehe `CLAUDE.md`).

Research-Wissen (Papers, Strategie-Findings) gehört NICHT hierher, sondern
in die PARA-Struktur (`projects/`, `areas/`, `resources/`, `archive/`,
siehe `README.md`). Hier geht es nur um: was läuft gerade, was ist zuletzt
passiert, was steht an.

---

## ▶️ Als Nächstes

1. **`data_lake/`-Paket nie committet** (gefunden 2026-09-06): treibt seit
   09-04 alle 6 Live-Beine von Funded-Portfolio-Bridge (echtes Geld), hat
   aber null Git-Commits — existiert nur lokal, kein Backup. Fix: `git add
   data_lake/` + Commit nachholen. Details: KW36-Weekly-Report Punkt 2.
2. ~~gold_asb: Historie-Cache greift nie~~ — **behoben 2026-09-06.**
   `stable_end_str` (Alt/Neu-Grenze) lief auf "gestern" (wandert täglich,
   verfehlte den Datums-Cache dadurch jeden Tag) → jetzt auf Monatsanfang
   stabilisiert (ändert sich nur 1x/Monat), "neues" Fenster deckt dafür den
   laufenden Monat ab (max. ~31 Tage, bleibt klein). Verifiziert: zwei
   Aufrufe lieferten identische 188 Zeilen, zweiter schneller. Voller
   Cache-Vorteil zeigt sich über die nächsten Tage.
3. **Manuelles Monatsjournal + Quant-System-Verschmelzung** (Nutzerwunsch
   2026-09-02): händisches Monatsjournal + Plan, wie manuelles Trading und
   das Quant-System sinnvoll verschmolzen werden — braucht zuerst ein
   klärendes Gespräch (Format, Kennzahlen). Noch nichts gebaut.
3. ~~M5-Scan-Frequenz für CTNL Continuation + NY-Open ORB~~ — **erledigt,
   live seit 2026-09-04.** Neue `data_lake`-Lane `"fast5"` + eigener
   Fast-Task, Cross-Prozess-Lock gegen Doppel-Ausführung. Nutzer hat
   Testlauf + beide Scheduled Tasks selbst verifiziert. Details: CHANGELOG.
4. ~~Funded-Portfolio-Bridge: redundante Scans vermeiden~~ — **erledigt
   2026-09-03.** MT5 als Datenquellen-Ersatz geprüft und verworfen (deckt
   nur 9 von ~30 gebrauchten Instrumenten ab). Stattdessen `run_once.py`
   umgebaut: 6 Scans laufen jetzt 1x pro Bridge-Lauf statt 1x pro Konto.
   Nebenfund: `tvDatafeed`-Pro-Login entfernt (TradingView-Captcha-Wall).
   Details: CHANGELOG.

---

## 📋 Offene Punkte (nach Priorität)

Zusammengeführt aus "Braucht deine Bestätigung" + "Offene Aufgaben" — nach
Priorität sortiert, erledigte Punkte pro Kategorie unten. Höchste Priorität:
offene Projekte mit konkretem nächstem Schritt (aktuell keins offen — der
gold_asb-Cache-Bug oben läuft über "Als Nächstes"). Danach: Bestätigungs-
Bedarf vor generischem Aufräumen.

### 🔍 Braucht deine Bestätigung

Punkte, bei denen etwas unklar/widersprüchlich ist oder eine Annahme von mir
noch nicht von dir bestätigt wurde. Erledigte Punkte werden entfernt, nicht
abgehakt-und-liegengelassen.

- **Lokaler `main` 64 vor / 1 hinter `origin/main`** (2026-09-06): Push
  seitdem "rejected - fetch first" — Bot-Snapshots (States, Dashboard)
  liegen nur noch lokal, nicht auf GitHub. Vermutlich 1 fremder Commit
  (`7616951`) ungemergt. Merge/Pull auf einem Repo mit mehreren
  Auto-Commit-Bots nicht ungefragt — braucht dein OK.
- ~~5-Min-Fast-Trigger: 3 Engineering-Entscheidungen unbestätigt~~ —
  **bestätigt 2026-09-06** (Nutzerauftrag, echt nachgeprüft statt pauschal
  abgenickt): M15-Zusatz für SP500/US30/NASDAQ (Begründung Opening-Range-
  Timing schlüssig), `account_state_lock()` (Code gelesen — identische
  `os.O_CREAT|O_EXCL`-Technik, die unabhängig davon am selben Tag für
  `data_lake/manifest.py`s analoges Problem gebaut wurde, starkes Indiz für
  den richtigen Ansatz), Retry-Parameter 3x/3s/20s im Fast-Pfad direkt im
  Code verifiziert (`run_once_fast.py`). Alle drei sinnvoll.
- ~~Funded-Portfolio-Bridge: kein "Signal zu alt"-Schutz beim Echt-Entry~~
  — **Korrektur 2026-09-06**: war bereits längst umgesetzt
  (`MAX_SIGNAL_AGE_MINUTES_FOR_ENTRY=60` in `_process_leg()`, gilt generisch
  für alle Beine, per Code-Check bestätigt) — der gegenteilige "noch
  offen"-Eintrag hier war ein stehengebliebener Duplikat-Stand vom selben
  Tag, jetzt entfernt.
- ~~2 neue Funded-Portfolio-Bridge-Konten (TTP #504069845, IQ 15514)
  verbanden nicht~~ — **Korrektur 2026-09-06**: war bereits am 2026-09-03
  gelöst (Status-Tabelle unten zeigt seitdem "alle 4 verbunden"), der
  "Fix in Arbeit"-Eintrag hier war stehengeblieben. Tatsächliche Ursache:
  "DLL-Importe zulassen" (eigene Einstellung, getrennt von AutoTrading) +
  ein strukturell defekter Terminal-Ordner → Konten auf funktionierende
  Ordner umgehängt.
- ~~Merge-Konflikt in diesem Abschnitt + CHANGELOG~~ — nachgeprüft
  2026-09-04, keine Widersprüche/Duplikate gefunden.
- ~~CLS Practical scheitert wiederholt an `dukascopy_python`~~ — Retries
  in allen 3 Bridges erhöht (3→6 Versuche), 2026-09-02. Bug bleibt in der
  Bibliothek selbst, nur Toleranz erhöht.
- ~~Rechner-/Task-Lücke ~9h über Nacht~~ — Ursache: Windows Modern Standby
  über AC-Display-Idle-Timeout, nicht "Rechner aus". Cache-Validierung +
  WakeToRun + neuer Bridge-Watchdog als Absicherung, 2026-09-02.
- ~~Telegram-Logik uneinheitlich zwischen den drei Portfolios~~ —
  `fk_instant_funding` auf gleiche Queue-Infrastruktur gehoben, 2026-09-02.
- ~~`fk_instant_funding/paper_bot.py`: letzte ORB-Kopie auf altem Stand~~ —
  nachgezogen 2026-09-02, alle 3 aktiven ORB-Träger jetzt gleich.
- ~~Funded-Portfolio-Bridge OU-Modell-Bein meldete nie offene Signale~~ —
  Root Cause (offene Positionen fielen unter den Tisch) + NYSE-Gate
  gefixt, 2026-09-02.
- ~~EK-Portfolio-Bridge: vage "cls_practical: unerwarteter Fehler"~~ —
  geklärt 2026-09-04: bekannter dukascopy-90s-Hang, kein neuer Fehler.
- ~~EK-Portfolio-Bridge: NASDAQ-Ticket 262117522 hing am Session-Ende-Exit~~
  — geschlossen 2026-09-04 (Comment-Feld für Tickmill zu lang, gekappt).
- ~~EK-Portfolio-Bridge: US30 "Invalid stops"~~ — zweiter Bug gefunden
  2026-09-04 (TP auf falscher Seite bei LONG), SL-Prüfung aufs TP erweitert.
- ~~2 neue Funded-Portfolio-Bridge-Konten waren bereits anderweitig
  vergeben~~ — bewusste Konsolidierung (Nutzerentscheid 2026-09-02).
- ~~`dukascopy_python` hing komplett fest, ohne Timeout~~ — neue
  `_call_with_timeout()` (90s) um jeden Retry, 2026-09-02, alle 3 Bridges.
- ~~`OU-Modell-ScannerHourly` verwaist~~ — bewusst weiterlaufen lassen
  (Streamlit-Seite braucht ihn), 2026-09-02.

### Offene Aufgaben

**Mittel**
- **12 unverarbeitete Clippings seit 2026-09-03** in `knowledge/Clippings/`
  (Edge-Genesis/-Decay, Risk-Factor-Investing, Sektor-Rotation, u.a.) —
  noch nicht durch den CODE-Prozess.
- ~~Second-Brain/Dashboard-Struktur: Feedback nach ein paar Tagen
  einholen~~ — erhalten 2026-09-06: Nutzer sehr zufrieden mit dem neuen
  Workflow, Dashboard passt gut rein. Redesign (Prioritäten-Sortierung,
  kürzere Texte, Status-Tabellen-Split) heute umgesetzt.
- ~~5 unverarbeitete Clippings~~ — verarbeitet 2026-09-02, Ordner geleert.
- ~~EK-Portfolio-Bridge: Spread-Stunden-Pause (23:00)~~ — bewusst
  zurückgestellt 2026-09-01 (0% historische Relevanz, noch nicht lohnend
  genug) — nicht erneut vorschlagen ohne neuen Trigger.
- ~~EK-Portfolio-Bridge/NY-Open-ORB: "Invalid stops"~~ — behoben
  2026-09-02.

**Niedrig**
- `knowledge/`-Altlasten (Lint 2026-09-01): tote Wikilinks
  (`[[cls-practical]]`, `[[gap-fade]]`, `[[execution-overlay]]`) + 8
  verwaiste Seiten, meist unkritisch. Details: Lint-Output/CHANGELOG.

## Status — was läuft gerade wirklich

| Bot/Bridge                                              | Konto/Broker                                                                             | Modus                                                                                        | Task Scheduler                  | Zuletzt geprüft |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------- | --------------- |
| EK-Portfolio-Bridge                                     | Tickmill Live (55918977)                                                                 | **LIVE — echtes Geld** (6 Dukascopy-Beine: btc/gold_asb/cls_practical/ctnl x2/ou_modell)     | Ready (alle 15 Min, Mo–Fr)      | 2026-09-03      |
| EK-Portfolio-Bridge-Fast                                | Tickmill Live (55918977, geteiltes Terminal)                                             | **LIVE — echtes Geld** (3 MT5-native Beine: ORB/Gold-Silber/Trend-Pullback, kein Dukascopy)  | Ready (alle 2 Min, Mo–Fr)       | 2026-09-03      |
| FKInstantFunding-MT5-Bridge                             | BeyondIQCapital (17764)                                                                  | DRY_RUN                                                                                      | Ready (stündlich)               | 2026-09-02      |
| FK-Instant-Funding-Paper                                | — (reine Simulation)                                                                     | Paper + Telegram                                                                             | Ready (stündlich)               | 2026-09-01      |
| OU-Modell-ScannerHourly                                 | — (nur Signal-Scan, kein Order-Versand)                                                  | Scanner + Telegram (3x täglich: 15:35/18:35/21:35)                                           | Ready (Mo–Fr, US-Handelszeiten) | 2026-09-02      |
| Forex-Weekly-Report                                     | —                                                                                        | Report-Generator                                                                             | Ready                           | 2026-09-02      |
| Bridge-Watchdog                                         | — (nur Log-Frische, kein Order-Bezug)                                                    | Heartbeat-Alarm + Status-Snapshot ins Repo                                                   | Ready (alle 30 Min)             | 2026-09-02      |
| Funded-Portfolio-Bridge (TTP+IQ Markets, 6 Beine)       | TTP Konto 2 (504072729) + TTP Konto 1 (504069845) + BeyondIQCapital (16054) + BeyondIQCapital (15514) — **alle 4 verbunden** | **LIVE — DRY_RUN=False** (alle 6 Beine `source="lake"`, siehe Data-Lake-Pilot) | Ready (alle 15 Min, Mo–Fr)      | 2026-09-04      |
| Funded-Portfolio-Bridge-Fast                            | Gleiche 4 Konten (geteilte Terminals)                                                    | **LIVE — DRY_RUN=False** (nur ctnl_continuation + orb_sp500/us30/nasdaq, `source="lake"`)   | Ready (alle 5 Min, Mo–Fr)       | 2026-09-04      |
| DataLake-Ingest-Fast                                    | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt `data_lake_store/` für Funded-Portfolio-Bridge (19 Keys, 15-Min-Kadenz)                | Ready (alle 15 Min, Mo–Fr)      | 2026-09-04      |
| DataLake-Ingest-Fast5                                   | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt 7 M5/M15-Timing-kritische Keys für ctnl_continuation/orb                               | Ready (alle 5 Min, Mo–Fr)       | 2026-09-04      |
| DataLake-Ingest-Slow                                    | — (nur Datenabruf, kein Order-Bezug)                                                     | Füllt OU-Modell-Universum (~59 Ticker) via yfinance                                          | Ready (stündlich, Mo–Fr)        | 2026-09-04      |
| Dashboard-Telegram-Digest (neu)                         | — (nur Lesezugriff auf DASHBOARD.md, kein Order-Bezug)                                   | Schickt offene Punkte aus DASHBOARD.md per Telegram                                          | Ready (täglich 8:00)            | 2026-09-06      |

Live-Status aller drei Portfolio-Bridges jetzt auch als Streamlit-Seiten
(„Portfolio-Bridges" in der Sidebar) — lesen `bridge_status/snapshot.json`,
das der Bridge-Watchdog alle 30 Min. committet.

_Letzter Lint-Check (tote Wikilinks, veraltete Daten, Widersprüche,
verwaiste Seiten, unverarbeitete Clippings): 2026-09-01, `knowledge/scripts/lint.py`
um Clippings-Check erweitert (siehe Skill `second-brain-lint`). Ergebnis: 0
veraltete Statustabellen-Daten, 8 verwaiste Seiten, mehrere tote Wikilinks,
5 unverarbeitete Clippings (inzwischen verarbeitet, siehe "Offene Aufgaben"
unten). Widersprüche (c) nicht vollständig manuell durchgegangen, nur
stichprobenartig — zwei sind beim heutigen Redesign per Code-Check
aufgefallen und aufgelöst (siehe "🔍 Braucht deine Bestätigung" oben)._

## Status — aktuell nicht aktiv

| Bot/Bridge                                              | Konto/Broker                                                                             | Status                                                                                          | Task Scheduler | Zuletzt geprüft |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------- | --------------- |
| Challenge Portfolio (Paper-Bot, `challenge_portfolio/`) | — (reine Simulation)                                                                     | Paper-Bot fertig entwickelt, kein Task angelegt                                                | —              | 2026-09-01      |
| BTC-EMA-Cross-Bridge/-Scan                              | Binance / BeyondIQCapital (15514, geteilt mit GoldASB)                                   | aufgelöst — Konto jetzt bei Funded-Portfolio-Bridge, `ACCOUNTS_MT5` leer                       | Disabled       | 2026-09-02      |
| CLS-Practical-Bridge/-Scan                              | —                                                                                        | aufgelöst — Logik steckt bereits in allen drei Portfolio-Bots                                 | Disabled       | 2026-09-02      |
| CTNL-Edge-FK-Paper                                      | —                                                                                        | aufgelöst — Logik steckt bereits in allen drei Portfolio-Bots                                 | Disabled       | 2026-09-02      |
| CTNL-Edge-MT5-Bridge                                    | BeyondIQCapital (16054)                                                                  | aufgelöst — Konto/Terminal bereits bei Funded-Portfolio-Bridge live                            | Disabled       | 2026-09-01      |
| Gold-ASB-Scan / GoldASB-MT5-Bridge                      | BeyondIQCapital (15514)                                                                  | aufgelöst — Konto jetzt bei Funded-Portfolio-Bridge, `ACCOUNTS` leer                           | Disabled       | 2026-09-02      |
| OU-Modell-MT5-Bridge/-DailyLog/-Heartbeat               | —                                                                                         | aufgelöst — Konto jetzt bei Funded-Portfolio-Bridge, `ACCOUNTS` komplett leer                  | Disabled       | 2026-09-02      |
| EK-Portfolio-Paper                                      | —                                                                                        | pausiert (Paper-Zwilling von EK-Portfolio-Bridge, gehört zum Portfolio)                        | Disabled       | 2026-09-01      |

## 💡 Ideen-Inbox (unsortiert, später einordnen)

Kurz einfangen, was gerade auftaucht, ohne das aktuelle Thema zu verlassen —
wird bei Gelegenheit einsortiert (Offene Aufgaben, PARA-Struktur, oder
bewusst verworfen), nicht hier für immer liegen gelassen.

- **Periodischer `/doctor`-Check** (2026-09-04): zurückgestellt, noch keine
  nennenswerte Skill/MCP-Altlast bei aktuell nur 2 Skills.
- **CFDs → echte Futures umstellen** (2026-09-03): zwei getrennte,
  unentschiedene Punkte — (a) "echtere" Daten, aber eigene Rollover-Logik +
  Neuvalidierung nötig; (b) eigene Futures-Challenges bei Prop-Firms als
  möglicher neuer Track.
- **OU-Modell-Scanner ggf. komplett auf Telegram umstellen** (2026-09-02):
  Website bleibt vorerst, nicht entschieden.
- **PDFs/Bücher bulk-einbinden** (2026-09-01): prüfen ob
  `paper_dropbox/`-Pipeline dafür wiederverwendbar ist.
- **TTP/IQ ORB-Exits laufen pro Konto unabhängig auseinander** (2026-09-02):
  kein Bug (beide folgen korrekt ihrer Regel), aber noch nicht bewertet ob
  Exits kontoübergreifend synchronisiert werden sollten.
- **Stocks-in-Play 5-Min-ORB als neue Asset-Klasse** (2026-09-01, Paper
  Zarattini/Barbon/Aziz 2024, siehe [[opening-range-breakout]]): braucht
  neue Datenquelle (breites US-Aktienuniversum) + eigene Selektionslogik —
  eigenständige Idee, kein Filter-Add-on.

## Letzte Aktivität

_(Auszug — vollständiges Log in [CHANGELOG.md](CHANGELOG.md))_

- 2026-09-06 — Neuer Scheduled Task `Dashboard-Telegram-Digest`: schickt
  jeden Morgen 8:00 die offenen Punkte aus diesem Dashboard per Telegram
  (Nutzerwunsch). Details: CHANGELOG.
- 2026-09-04 — Second Brain: neuer Skill `handoff` (+ Inbox
  `knowledge/_handoff/`) für Session-Übergaben am Kontextfenster-Limit,
  aus dem "Everlast AI"-Clip übernommen (3 der 4 vorgeschlagenen Ideen
  bewusst verworfen/zurückgestellt, siehe `resources/second-brain-methodik.md`).
- 2026-09-04 — Data-Lake-Pilot gebaut + live geschaltet: Funded-Portfolio-
  Bridges 6 Beine lesen jetzt aus einem lokalen Parquet-Lake
  (`data_lake/`) statt live von Dukascopy/TradingView/yfinance. Neue
  Scheduled Tasks `DataLake-Ingest-Fast`/`-Slow`. Vollstaendig end-to-end
  verifiziert (Seed-Laeufe, `run_shared_scans()` direkt gegen die echte
  Config, kuenstlicher Stale-Test) — siehe CHANGELOG fuer Details. EK-
  Portfolio-Bridge/FK Instant Funding folgen erst nach Bewaehrung.
- 2026-09-04 — CTNL-eigener Kill-Switch (Stand-alone Cont+Rev-Drawdown
  gegen die Phase-6-P5-Schwelle) in EK-Portfolio/Challenge-Portfolio/FK
  Instant Funding nachgeruestet, nachdem er bei der Portfolio-Konsolidierung
  nicht automatisch mit uebernommen wurde — siehe CHANGELOG.
- 2026-09-03 (spät) — Bridge Error Monitor: dritte Lücke im heutigen OHLC-
  Validierungsfix geschlossen (`fetch_2y_yield_daily()` in
  `cls_practical/data.py`, siehe CHANGELOG). Zwei neue Echtgeld-Befunde auf
  EK-Portfolio-Bridge zur Bestätigung im Dashboard vermerkt: NASDAQ-Ticket
  262117522 scheitert wiederholt am Session-Ende-Exit, US30-Order erneut
  mit "Invalid stops" (derselbe, am 2026-09-02 als behoben dokumentierte
  Fehler) gescheitert.
- 2026-09-03 — Bridge Error Monitor: den am 2026-09-02 dokumentierten, aber
  nie tatsächlich umgesetzten "OHLC vor dem Cachen validieren"-Fix jetzt
  wirklich in `combined_strategy/data.py` + `cls_practical/data.py`
  ergänzt, nachdem derselbe `str`/`float`-Fehler heute erneut in drei
  Beinen gleichzeitig auftrat. Neue vage Fehlerzeile auf EK-Portfolio-
  Bridge zur Bestätigung im Dashboard vermerkt.
- 2026-09-03 — Funded-Portfolio-Bridge: redundante Scans behoben (6 Scans
  1x/Lauf statt 1x/Konto) + tvDatafeed-Pro-Login entfernt (TradingView-
  Captcha-Wall, seit 2026-09-01 taeglich hunderte Signin-Fehler). MT5 als
  Dukascopy-Ersatz geprueft und verworfen (Instrumenten-Abdeckung zu duenn).
- 2026-09-02 — Second Brain: 5 offene Clippings verarbeitet (CODE-Prozess) —
  3 Claude-Workflow-Videos als neue Einträge in
  `resources/second-brain-methodik.md`, 1 Trading-Video (Order Flow, nicht
  quant-übertragbar) als neue `resources/order-flow-trading.md`, 1 bestätigtes
  Duplikat. 4 Workflow-Verbesserungsideen daraus in DASHBOARD "Braucht deine
  Bestätigung" vermerkt. `Clippings/`-Ordner danach geleert.
- 2026-09-01 — Second Brain: Scope von `strategie-backlog-inventar.md`
  eingegrenzt (nur aktuell relevante Strategien + Filter mit echtem
  Mehrwert, kein Vollsweep über alle Ordner mehr), 5 echte Lücken bei
  laufenden/pausierten Bots identifiziert (`asian_range_breakout`,
  `cls_practical`, `btc_ema_cross`, `ek_portfolio`, OU-Modell). Dabei
  Task Scheduler + alle Live-Bridge-`DRY_RUN`-Flags gegen die Statustabelle
  geprüft — keine Abweichung gefunden.
- 2026-09-01 — EK-Portfolio: Echtgeld-Bugfix (Gold-ASB-Scan crashte seit
  11:30 bei jedem Lauf, tz-Vergleichsfehler) + Dukascopy-Retry in 3 Beinen
  nachgezogen. Verifiziert per fehlerfreiem 13-Bein-Lauf um 12:15.
- 2026-09-01 — Funded-Portfolio-Bridge: Scheduled Task angelegt (alle 15
  Min Mo–Fr) + 2 Bugs beim ersten automatischen Lauf gefunden/behoben
  (endlos wiederholte "verpasst"-Meldung, falscher `entry_price` im State).
- 2026-09-01 — Funded-Portfolio-Bridge (TTP/IQ Markets) auf `DRY_RUN=False`
  gestellt, erste 2 echten Orders platziert; OU-Modell/CTNL-Edge-MT5-Bridge
  sauber von den Zielkonten abgekoppelt.
- 2026-09-01 — 5 verwaiste MT5-Terminals geschlossen, nur die 2 aktiven blieben offen.
- 2026-09-01 — Challenge Portfolio: CTNL-Reversal-Kaskade gekappt + OU-Modell-Import-Fix (`69f9ca6`).
- 2026-09-01 — EK-Portfolio: CTNL-Reversal-Kaskade auf reales 3er-Limit gekappt (`c195924`).
- 2026-08-31 — FK Instant Funding: `scan_errors_today` auf lokalen Kalendertag umgestellt (`adc7d7c`).
- 2026-08-29 — Wochenend-/Spread-Stunden-Sperre auf EK-Portfolio + CTNL-Edge-FK-Paper ausgeweitet (`5fcf1da`).
- 2026-08-29 — FK Instant Funding: Wochenend-/Spread-Stunden-Sperre + UTC/Lokalzeit-Bug behoben (`79df9f3`).
- 2026-08-29 — FK Instant Funding: eigenes Telegram-Layout + gebündelte Nachrichten (`8f9a11a`).
- 2026-08-29 — FK Instant Funding: Gewichts-Optimierung + `CAPITAL_WEIGHT`-Umbau (`59ba4df`, `11f8979`).
