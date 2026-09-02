# Dashboard

**Stand: 2026-09-02** _(wird bei jeder Session von Claude auf das aktuelle
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

## Status — was läuft gerade wirklich

| Bot/Bridge                                              | Konto/Broker                                                                             | Modus                                                                                        | Task Scheduler                  | Zuletzt geprüft |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------- | --------------- |
| EK-Portfolio-Bridge                                     | Tickmill Live (55918977)                                                                 | **LIVE — echtes Geld**                                                                       | Ready (alle 15 Min, Mo–Fr)      | 2026-09-01      |
| FKInstantFunding-MT5-Bridge                             | BeyondIQCapital (17764)                                                                  | DRY_RUN                                                                                      | Ready (stündlich)               | 2026-09-01      |
| FK-Instant-Funding-Paper                                | — (reine Simulation)                                                                     | Paper + Telegram                                                                             | Ready (stündlich)               | 2026-09-01      |
| OU-Modell-ScannerHourly                                 | — (nur Signal-Scan, kein Order-Versand)                                                  | Scanner                                                                                      | Ready (Mo–Fr, US-Handelszeiten) | 2026-09-01      |
| Forex-Weekly-Report                                     | —                                                                                        | Report-Generator                                                                             | Ready                           | 2026-09-01      |
| **Funded-Portfolio-Bridge** (TTP+IQ Markets, 6 Beine)   | TTP Konto 2 (504072729) + BeyondIQCapital (16054)                                        | **LIVE — DRY_RUN=False**, 2 echte Positionen offen (Gold ASB SHORT, Ticket 18202597/1284739) | Ready (alle 15 Min, Mo–Fr)      | 2026-09-01      |
| Challenge Portfolio (Paper-Bot, `challenge_portfolio/`) | — (reine Simulation)                                                                     | Paper-Bot fertig entwickelt                                                                  | Noch kein Task angelegt         | 2026-09-01      |
| BTC-EMA-Cross-Bridge/-Scan                              | Binance                                                                                  | LIVE (war), aktuell pausiert                                                                 | **Disabled**                    | 2026-09-01      |
| CLS-Practical-Bridge/-Scan                              | —                                                                                        | pausiert                                                                                     | Disabled                        | 2026-09-01      |
| CTNL-Edge-FK-Paper                                      | —                                                                                        | pausiert                                                                                     | Disabled                        | 2026-09-01      |
| CTNL-Edge-MT5-Bridge                                    | BeyondIQCapital (16054)                                                                  | **abgelöst durch Funded-Portfolio-Bridge**, Konto/Terminal jetzt dort live                   | Disabled                        | 2026-09-01      |
| Gold-ASB-Scan / GoldASB-MT5-Bridge                      | BeyondIQCapital (16054)                                                                  | pausiert                                                                                     | Disabled                        | 2026-09-01      |
| OU-Modell-MT5-Bridge/-DailyLog/-Heartbeat               | TTP Konto1 (Konto 2 komplett aus `ACCOUNTS` entfernt, jetzt bei Funded-Portfolio-Bridge) | pausiert                                                                                     | Disabled                        | 2026-09-01      |
| EK-Portfolio-Paper                                      | —                                                                                        | pausiert                                                                                     | Disabled                        | 2026-09-01      |

_Letzter Lint-Check (tote Wikilinks, veraltete Daten, Widersprüche,
verwaiste Seiten, unverarbeitete Clippings): 2026-09-01, `knowledge/scripts/lint.py`
um Clippings-Check erweitert (siehe Skill `second-brain-lint`). Ergebnis: 0
veraltete Statustabellen-Daten, 8 verwaiste Seiten, mehrere tote Wikilinks,
**5 unverarbeitete Clippings** (Details unten). Widersprüche (c) nicht
vollständig manuell durchgegangen, nur stichprobenartig._

## 🔍 Braucht deine Bestätigung

Punkte, bei denen etwas unklar/widersprüchlich ist oder eine Annahme von mir
noch nicht von dir bestätigt wurde. Erledigte Punkte werden entfernt, nicht
abgehakt-und-liegengelassen.

- **Rechner/Scheduled Tasks hatten heute Nacht eine ~9h-Lücke** (2026-09-02,
  letzter Lauf 01:15, naechster erst 10:15, betraf FKInstantFunding-MT5-Bridge
  UND Funded-Portfolio-Bridge gleichermassen — vermutlich Rechner-Schlaf/
  Standby). Der erste Catch-up-Lauf danach baute frische, sehr breite
  Cache-Dateien neu auf (`data_cache/combined/GOLD_*_2016-01-01_...parquet`)
  und produzierte dabei auf BEIDEN Bridges zeitgleich denselben Fehler in 5
  Beinen (Gold ASB/CLS Practical/Trend Pullback/CTNL Edge/Gold-Silber-
  Divergenz): `'>' not supported between instances of 'str' and 'float'`.
  Bei Funded-Portfolio-Bridge selbst geheilt (naechster Lauf 10:30 komplett
  sauber, keine Aenderung meinerseits noetig) — FK Instant Funding lief
  seitdem noch nicht erneut (stuendlich, naechster ~11:15), aber nach
  identischem Muster sehr wahrscheinlich ebenfalls schon wieder gesund.
  Root Cause nicht bis auf die Zeile verifiziert (liess sich nicht mehr
  reproduzieren, sobald der Cache einmal sauber aufgebaut war) — falls sich
  das nach künftigen Standby-Phasen wiederholt, lohnt sich ein genauerer
  Blick auf die betroffene Cache-Schicht (`combined_strategy/data.py` o.ä.).
  Falls der naechtliche Rechner-Standby nicht gewollt ist, waere das
  separat zu beheben (Energieeinstellungen), nicht Teil dieser Session.
- **Telegram-Logik NICHT auf demselben Stand bei allen drei Portfolios**
  (Nachfrage 2026-09-02): EK-Portfolio-Bridge (`core/telegram_notify.py`)
  und Funded-Portfolio-Bridge (`telegram_notify.py`) sind strukturell
  identisch (moderne `queue_message()`/`flush_queued_messages()`-Buendelung,
  jedes Bein kann von ueberall aus eine Nachricht einreihen). FK Instant
  Funding (`fk_instant_funding/telegram_notify.py`, treibt die "FK-Instant-
  Funding-Paper"-Task — NICHT `FKInstantFunding-MT5-Bridge`, die hat
  ueberhaupt kein Telegram) hat nur ein nacktes `send_telegram_message()`,
  keine `queue_message()`/`flush_queued_messages()` — Buendelung passiert
  stattdessen ueber eine lokale Liste direkt in `paper_bot.py::scan_once()`,
  aelteres Vor-Refactor-Muster. Sichtbares Ergebnis (eine gebuendelte
  "Scan-Update"-Nachricht pro Lauf) ist gleich, Code ist es nicht. Soll ich
  `fk_instant_funding` auf das gemeinsame Muster nachziehen (reines
  DRY_RUN/Paper-Bein, kein Echtgeld-Risiko)?

- **`fk_instant_funding/paper_bot.py`** (treibt FKInstantFunding-MT5-Bridge,
  **DRY_RUN**, kein echtes Geld) ist die einzige verbliebene ORB-Kopie auf
  altem Stand: ein gemeinsames `ORB_EXIT_CFG` fuer alle 3 Instrumente, kein
  NASDAQ-EOD-Exit, kein Teilausstieg. Noch offen: nachziehen oder so lassen?
  (`ek_portfolio/paper_bot.py` bewusst NICHT nachgezogen — Nutzerentscheid
  2026-09-02: bleibt pausiert/Disabled, da EK-Portfolio-Bridge bereits live
  mit echtem Geld dieselbe Logik faehrt; ein zusaetzlich synchronisierter
  Paper-Bot ohne Zweck.)

- [x] ~~Funded-Portfolio-Bridge OU-Modell-Bein meldete nie ein offenes Signal~~
  — Root Cause gefunden UND behoben 2026-09-02 (nicht nur die vermutete
  Config-Divergenz): `ou_portfolio.simulate_bracket_portfolio()` liess jede
  noch OFFENE Position beim Rueckgabe-Zeitpunkt still unter den Tisch fallen,
  nur GESCHLOSSENE Trades kamen in `trades` an — das Bein konnte dadurch
  STRUKTURELL nie "data_end" (= aktuell offen/handelbar) melden, unabhaengig
  von Config oder Kriterien. Fix: neuer `include_open_positions`-Parameter
  (additiv, Default `False`, kein anderer Aufrufer betroffen). Verifiziert an
  FAST/SPG/SYY (denselben 3 Tickern, die der Standalone-Scanner um 21:35
  fand) — erscheinen nach dem Fix korrekt mit `entry_date=2026-08-31,
  reason=data_end`. Naechster Live-Lauf von Funded-Portfolio-Bridge wird
  dadurch voraussichtlich 3 neue echte Entries (TTP+IQ) platzieren. Die
  Frage "eigene Implementierung vs. gemeinsame CSV-Quelle wie EK" bleibt
  trotzdem offen, jetzt aber nicht mehr dringend (Bein funktioniert wieder).
  **Sofortiger Folgefund** (00:05 Uhr, direkt nachdem das Bein zum ersten
  Mal feuerte): ohne NYSE-Handelszeiten-Gate versuchte die Bridge um
  Mitternacht echte Aktien-Entries (ADI/FAST) — TTP "Market closed",
  IQMARKETS "no_tick". Ebenfalls 2026-09-02 gefixt (`run_once.py::
  _nyse_is_open()`, identisches Muster zu EK), nur neue Entries gegated,
  Exits laufen weiter uneingeschraenkt. Nur `py_compile`-geprueft.

- **Funded-Portfolio-Bridge (TTP/IQ) hat noch keinen "Signal zu alt"-Schutz**
  beim Echt-Entry (`_process_leg()`), anders als der ORB-Fix heute in
  EK-Portfolio-Bridge. Der erste reale Gold-ASB-Entry heute ist genau daran
  hängen geblieben: Signal um 05:15 UTC, aber real erst 09:30 UTC gefüllt
  (~4h15 später, weil die Bridge da überhaupt zum ersten Mal live ging) —
  zu dem Zeitpunkt war der Kurs schon ~55-58 Punkte weiter gelaufen, der
  Short kam praktisch erst nach der Bewegung rein. Einmaliger Umstiegs-
  Effekt (Bridge lief vorher gar nicht), kein wiederkehrender Bug — aber
  falls die Bridge künftig mal länger pausiert/ausfällt, würde sich das
  exakt wiederholen. Soll ich denselben Alters-Check wie bei ORB (Signal
  überspringen statt zum längst gelaufenen Kurs zu jagen) hier ebenfalls
  einbauen? Nicht selbständig gemacht, weil das echtes Geld + eine gerade
  offene Position betrifft.

## 💡 Ideen-Inbox (unsortiert, später einordnen)

Kurz einfangen, was gerade auftaucht, ohne das aktuelle Thema zu verlassen —
wird bei Gelegenheit einsortiert (in Offene Aufgaben, PARA-Struktur, oder
bewusst verworfen), nicht hier für immer liegen gelassen. Genau der Ort für
"das könnte auch noch interessant sein", ohne dass es das gerade laufende
Thema verdrängt oder verloren geht.

- **PDFs/Bücher bulk-einbinden** (2026-09-01): viele Bücher/PDFs vorhanden,
  die sinnvoll integriert werden könnten, ohne sie einzeln in den Chat
  schicken zu müssen. Prüfen, ob `paper_dropbox/`/`paper_research/`
  (bestehende "PDF rein, Extraktion + Auto-Backtest raus"-Pipeline, siehe
  README.md) dafür wiederverwendbar ist, oder ob Bücher (anders als
  Research-Paper) einen eigenen Weg brauchen. Noch nicht bearbeitet.
- **Stocks-in-Play 5-Min-ORB als neue Asset-Klasse** (2026-09-01, aus Paper
  "A Profitable Day Trading Strategy For The U.S. Equity Market",
  Zarattini/Barbon/Aziz 2024, siehe [[opening-range-breakout]]): 5-Min-ORB
  auf einem breiten US-Aktien-Universum (~7.000 Titel), gefiltert auf die
  Top-20-Relative-Volume-Aktien pro Tag, zeigte im Paper Sharpe 2.81/Alpha
  36%/Jahr - deutlich staerker als der reine Index-ORB-Ansatz
  ([[ny-open-orb-sp500]]). Braucht eine neue Datenquelle (breites,
  survivorship-bias-freies US-Aktienuniversum) und eigene Selektionslogik -
  kein einfaches Filter-Add-on zur bestehenden Strategie, daher eigenstaendige
  Idee statt Teil des laufenden Projekts. Noch nicht bearbeitet.

## Offene Aufgaben

**Mittel**
- [ ] **5 unverarbeitete Clippings warten** (per Lint-Check-Erweiterung
  2026-09-01 gefunden, `python knowledge/scripts/lint.py` prüft das jetzt
  automatisch mit, siehe Skill `second-brain-lint`):
  - Trading: `Trading WORLD CHAMPION Reveals the Orderflow Strategy That
    Won the Robbins Cup (Step-by-Step).md`
  - Claude-Workflow/Token-Sparen: `Claude nutzen wie die Top 1 %
    Schritt-für-Schritt-Anleitung.md`, `Du verschwendest Tokens in Claude -
    Ändere diese 5 Einstellungen!.md`, `Nie wieder Claude-Limits 12 Tipps
    für 20x mehr Leistung aus deinem Claude-Plan!.md`
  - `Der einfachste Einstieg in Second Brains! 1.md` — vermutlich Duplikat
    des bereits verarbeiteten Clips (`resources/second-brain-methodik.md`),
    nicht automatisch gelöscht, nur zur Prüfung markiert.
  - Noch nicht distilliert, auf Zuruf (Nutzer hat noch nicht "leg los" gesagt).
- [ ] Second-Brain/Dashboard-Struktur (dieses Dokument) — nach ein paar
  Tagen Nutzung Feedback einholen, ob Format/Umfang passt.
- [x] ~~EK-Portfolio-Bridge: Spread-Stunden-Pause (23:00)~~ — am 2026-09-01
  bewusst zurückgestellt. Backtest über alle 7 Strategien (704 historische
  Trades) zeigt 0,0% Entries in der Stunde 23:00 Europe/Berlin bei jeder
  einzelnen — die Pause hätte historisch nichts gekostet, wäre aber bei den
  aktuellen Edges nach Nutzereinschätzung noch nicht sinnvoll genug, um sie
  einzubauen. Nicht wieder von selbst vorschlagen, außer neue Legs mit
  potenziell später Entry-Zeit kommen dazu.
- [x] ~~EK-Portfolio-Bridge / NY-Open-ORB: SP500/US30-Entries "Invalid stops"~~
  — behoben 2026-09-02 (Details CHANGELOG.md), nur `py_compile`-geprüft,
  nächster echter Live-Lauf verifiziert es noch nicht endgültig.

**Niedrig**
- [ ] `knowledge/`-Altlasten (Lint-Check 2026-09-01, Details s. Skript-Output
  `python knowledge/scripts/lint.py`):
  - Tote Wikilinks ohne größeren Zusammenhang: `[[cls-practical]]`
    (`archive/london-range-bos-retest-eurusd.md`), `[[gap-fade]]` und
    `[[execution-overlay]]` (beide `resources/fx-microstructure.md`).
  - 8 verwaiste Seiten ohne eingehende Wikilinks: `archive/ipda-zyklus-eurusd.md`,
    `archive/london-cls-breakout-eurusd.md`,
    `archive/london-range-bos-retest-eurusd.md`,
    `areas/paper-bot-architecture.md`,
    `projects/challenge-portfolio-ttp-icapital.md`,
    `projects/persoenlicher-tradingplan-validierung.md`,
    `projects/strategie-backlog-inventar.md`,
    `resources/second-brain-methodik.md`. Meiste unkritisch (Projects
    verlinken oft nur raus), aber `challenge-portfolio-ttp-icapital` könnte
    noch einen Rücklink von einer verwandten Resource/Area vertragen.
    (`ny-open-orb-sp500` 2026-09-01 aufgelöst: neue Resource
    `resources/opening-range-breakout.md` verlinkt jetzt dorthin.)

## Letzte Aktivität

_(Auszug — vollständiges Log in [CHANGELOG.md](CHANGELOG.md))_

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
