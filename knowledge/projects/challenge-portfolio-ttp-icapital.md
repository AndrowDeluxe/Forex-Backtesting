# Project: Challenge-Portfolio (Funded Portfolio) -- TTP & IQ Markets/"I Capital"

**Ziel**: Das bereits validierte FK-Portfolio (`app_pages/portfolio_construction.py`,
Tab "FK-Portfolio") von einer reinen Analyse-Seite zu echten Paper- und
(spaeter) Live-Bots mobilisieren -- fuer zwei Challenge-Regelwerke: TTP
(Tageslimit 3%, Gesamt-DD 7%, Ziel 10%) und IQ Markets (vom Nutzer "I
Capital" genannt -- identische Zahlen: kein Tageslimit, Gesamt-DD 6%, Ziel
8%, Positionslimit 1%; realer Broker dahinter ist BeyondIQCapital, siehe
[[gold-ctnl-edge-portfolio]]).

**Status** (2026-09-01): **LIVE** (`DRY_RUN=False`, Nutzerauftrag "stelle dry
run auf false dann gehen wir rein"). Erster echter Lauf platzierte 2 reale
Orders (Gold ASB SHORT, je 0.03 Lots): TTP Ticket **18202597** @ 4367.13,
IQ Markets Ticket **1284739** @ 4370.73 -- beide broker-seitig verifiziert
(korrekter SL 4456.56, kein TP, wie designed). Vorbedingung fuer den Go-Live
erfuellt: OU-Modell-MT5-Bridge/config.py's Konto-2-Eintrag (504072729)
komplett aus `ACCOUNTS` entfernt (nicht nur Task deaktiviert -- Konto 1,
echtes Geld, unveraendert), CTNL-Edge-MT5-Bridge mit Warnhinweis versehen
(Task war schon deaktiviert). Alte Solo-Bots koennen dieses Konto/Terminal
jetzt nicht mehr versehentlich gleichzeitig bespielen.

MT5-Bridge INKLUSIVE echter Order-Ausfuehrung, Telegram (gebuendelte
Scan-Update-Nachrichten + taeglicher Tagesabschluss, getrennt fuer "TTP
Challenge"/"IQ Challenge") UND echtem Risk-Management (1%-Positionsdeckel +
trailing Gesamt-Drawdown-Kill-Switch, beide gegen die ECHTE aktuelle
Kontoequity). Volles Fehler-Review durchgefuehrt (2026-09-01), 4 reale
Findings behoben + 2 Risk-Management-Fixes auf expliziten Nutzerauftrag
(siehe "Risk-Management-Nacharbeit") + 1 weiterer Fund direkt beim ersten
echten Lauf entdeckt und behoben (siehe "Erster Live-Lauf" unten).

## Erster Live-Lauf (2026-09-01) -- 1 Fund behoben

`place_market_entry()`s `result.price` (aus `mt5.order_send()`) kam fuer
beide ersten echten Order-Sends zuverlaessig als `0.0` zurueck, obwohl die
Position broker-seitig einwandfrei mit korrektem Preis offen war (per
`mt5.positions_get()` verifiziert: TTP 4367.13, IQ Markets 4370.73) --
`result.price` scheint fuer diesen Broker/diese Fuellart nicht robust. Betraf
NUR das State-Feld `entry_price` (rein informativ, floss in KEINE Risiko-
/Sizing-Berechnung ein, die lief bereits vorher mit dem Signal-Preis) --
keine Fehlausfuehrung, keine falsche Positionsgroesse. Fix: `place_market_
entry()` liest den echten Preis jetzt direkt aus der frisch georderneten
Position (`mt5.positions_get(ticket=result.order)[0].price_open`),
`result.price` bleibt nur Fallback. Die zwei bereits gespeicherten
State-Eintraege wurden nachtraeglich auf die echten Preise korrigiert.

## Risk-Management-Nacharbeit (2026-09-01, Nutzerauftrag: "wir wollen in
jedem Fall 1% der aktuellen Kontogroesse und auch der Max Drawdown ist
trailing und richtet sich nach der aktuellen Kontogroesse bei beiden
Anbietern")

1. **1%-Positionsdeckel jetzt dynamisch statt statisch**: sowohl im Paper-Bot
   (`compute_shared_equity()`) als auch in der Bridge (`_process_leg()`)
   wurde der vorher als Review-Fund dokumentierte statische $1'000-Deckel
   (abgeleitet vom $100k-Platzhalter) durch `MAX_POSITION_RISK_PCT * equity`
   ersetzt, mit der jeweils AKTUELLEN Equity (simuliert im Paper-Bot, real
   in der Bridge) zum Zeitpunkt jedes einzelnen Trades. `check_iqmarkets_
   rules()`s Invariantenpruefung ist entsprechend auf einen Pro-Zeile-
   Vergleich umgestellt (jeder Trade gegen SEINEN eigenen damaligen Deckel,
   nicht gegen einen globalen Wert).
2. **Neue trailing Gesamt-Drawdown-Kill-Switch-Logik in der Bridge**
   (`_check_risk_gate()`, vorher gab es dort GAR KEINE Regel-Durchsetzung
   gegen die echte Kontohistorie -- nur der Paper-Bot hatte das). Peak =
   hoechste je beobachtete ECHTE Kontoequity (bewegt sich nur nach oben,
   echtes Trailing), Kill-Switch bei -7% (TTP) / -6% (IQ Markets) relativ zu
   diesem Peak -- KEIN automatischer Reset (ein Gesamt-Drawdown-Bruch
   beendet die Challenge faktisch). TTP zusaetzlich: Tageslimit -3% gegen
   die letzte abgeschlossene Vortages-Equity, taeglich automatisch neu
   ausgewertet (kein manueller Reset noetig). Ein aktiver Kill-Switch/
   Tageslimit stoppt NUR neue Entries (`entries_allowed`-Parameter durch
   `_process_leg()`/`process_account_signals()` durchgereicht) -- bereits
   offene Positionen werden unveraendert normal weiter ueber den Re-Scan-
   Vergleich geschlossen, nie abrupt liegengelassen. Tagesabschluss zeigt
   jetzt zusaetzlich Trailing-DD + Kill-Switch-Status.
3. Beide Aenderungen per Unit-Tests verifiziert (7 Szenarien: Normalfall,
   Peak-Wachstum, Gesamt-DD-Bruch, kein Auto-Reset nach Erholung, TTP-
   Tageslimit-Bruch unabhaengig vom Gesamt-DD, taeglicher Auto-Reset des
   Tageslimits, IQ-Markets ohne Tageslimit) + echter End-zu-Ende-Lauf gegen
   beide Konten (DRY_RUN, keine Order gesendet).

## Telegram (2026-09-01, Nutzerwunsch: "dieselbe Anbindung wie fuer die
anderen beiden Portfolios")

Identisches Muster zu `fk_instant_funding/paper_bot.py`/`EK-Portfolio-Bridge`:
gebuendelte "Scan-Update"-Nachricht pro Lauf (`queue_message`/`flush_queued_
messages` in der Bridge, direkt in `scan_once()` im Paper-Bot) statt einer
Nachricht je Bein, plus EIN taeglicher Tagesabschluss (21 Uhr Europe/Berlin,
`_local_dt()`-korrekt) mit Gesundheits-Zeile (Scan-Fehler heute) + Equity/DD.
Getrennt in zwei Nachrichtenstroeme mit eigenem Banner: "TTP Challenge" und
"IQ Challenge" (`telegram_format.py` in der Bridge, `_challenge_message()` im
Paper-Bot). Scan-Fehler loesen keinen Sofort-Alarm mehr aus, nur noch die
Gesundheits-Zeile im Tagesabschluss (`scan_errors_today`-Tracking). Beide
Wege end-zu-end getestet (echte Telegram-Sends im DRY_RUN der Bridge, isolierte
dry_run-Pruefung im Paper-Bot).

## Fehler-Review (2026-09-01, Nutzerauftrag: "gesamte Logik, Ausfuehrung,
Risk Management ... auf Fehler pruefen")

4 reale Findings behoben:
1. **`resolve_symbol()` in der Bridge fehlte `mt5.symbol_select()`** -- CTNL-
   Edge-MT5-Bridge/executor.py (das Vorbild) hat das, meine Kopie nicht. Ohne
   Select liefert `symbol_info_tick()` fuer neu hinzugekommene Symbole (OU-
   Modell-Einzelaktien, ORB-Indizes -- auf diesen Konten vorher nie gehandelt)
   moeglicherweise leere/veraltete Daten -> Trades still verpasst (faellt
   sicher als "no_tick"-Fehler auf, keine Fehlorder, aber verpasste Chancen).
   Behoben.
2. **Bridge speicherte den theoretischen Signal-Entry-Preis statt des echten
   Broker-Fills** (`result["entry_price"]`) im State -- bei Slippage/Spread
   wich das ab. Behoben + per Mock-Test verifiziert.
3. **`check_iqmarkets_rules()`s Positionslimit-Pruefung nutzte `assert`** --
   wird mit `python -O` komplett entfernt, genau die "stille Annahme", die
   der eigene Docstring explizit ausschliessen wollte. Auf `raise ValueError`
   umgestellt.
4. **Kosmetisch, aber Telegram-relevant**: `_merge_trades()`s Entry/Exit-
   Zeilen trugen noch das alte "[Challenge Portfolio]"-Praefix, redundant
   unter dem neuen Banner. Entfernt.

**Nicht behoben, bewusst nur dokumentiert (Design-Frage, keine unilaterale
Aenderung)**: Der 1%-Positionsdeckel (`MAX_POSITION_RISK_DOLLARS`/`MAX_
POSITION_RISK_PCT`) ist ein STATISCHER Dollarbetrag ($1'000), abgeleitet von
`STARTING_EQUITY`=$100k (dem Paper-Bot-Platzhalter) -- NICHT von der
tatsaechlichen AKTUELLEN Kontoequity. Bei der aktuellen $100k-Kontogroesse
und den aktuellen Risikostufen ist das nie die bindende Grenze ($75-333 <<
$1'000), aber es ist NICHT wirklich "1% der aktuellen Equity" im woertlichen
Sinne von IQ Markets' Regel -- bei einem Konto, das deutlich UNTER $100k
faellt, wuerde der Deckel mehr als echte 1% zulassen. Sollte vor einem
DRY_RUN=False-Entscheid nochmal bewusst adressiert werden, falls die
Kontogroesse sich je deutlich vom $100k-Referenzwert entfernt.

**Positiv verifiziert (keine Aenderung noetig)**: Monte-Carlo-Klassifikations-
logik in `research_challenge_portfolio_6leg.py` (Pfad-Klassifikation Ziel
vs. Bruch vs. keins, Tie-Break-Verhalten) durchgerechnet, korrekt. CTNL-
Reversal-Konkurrenz-Deckelung (`_cap_concurrent_reversals`, bereits von
frueherer Session/Nutzerwunsch am 2026-09-01 eingebaut) verifiziert korrekt
-- greedy Intervall-Scheduling, verhindert, dass der Paper-Bot mehr
gleichzeitige Reversal-Positionen annimmt als eine echte Bridge je haette
ausfuehren koennen. Kommt der Bridge automatisch zugute (importiert
dieselbe `_scan_ctnl()`-Funktion).

## Roster & Risikostufen

6 Beine, gleichgewichtet (1/6 Kapitalanteil je Bein): Gold ASB (2.0%),
CLS Practical (1.5%), Trend Pullback (0.5%), CTNL Edge Continuation (0.5%) +
Reversal (0.15%), OU-Modell TTP-Teilmenge (1.0%), NY-Open ORB SP500+US30+
NASDAQ (1.0% kombiniert, 1/3 je Instrument). Positionsgroessen-Formel:
`risk_dollars = CAPITAL_WEIGHT (1/6) x internes Risiko/Trade x Konto-Equity`,
gedeckelt auf 1% des Startkapitals (erfuellt IQ Markets' Positionslimit
strukturell).

**ORB-Aufnahme-Entscheidung** (2026-08-27/28, `scripts/research_challenge_
portfolio_6leg.py`, Ergebnis in `portfolio_construction/results/
challenge_portfolio_6leg.json`): ORB als 6. Bein verbessert BEIDE Regelwerke
gleichzeitig auf allen Kennzahlen (TTP-Bruchwahrscheinlichkeit 1.6%->0.2%,
Median-Tage-bis-Ziel 168->153; IQ Markets Bruch 3.2%->0.9%, Tage 131->123;
CAGR 13.9%->15.6%, MaxDD -4.5%->-3.9%) dank nahezu-Null-Korrelation
(-0.07 bis +0.03) zu den anderen 5 Beinen. ORB-Bein bewusst aus den
AKTUELLEN Trade-Listen des `ny_open_orb/`-Moduls gebaut (`legs/trades_ny_orb_
{sp500,us30,nasdaq}.csv`), NICHT aus der veralteten `legs/orb_strategy_
r100.csv` (alte, verworfene `orb_strategy/`-Variante).

## Paper-Bot

`challenge_portfolio/paper_bot.py` (im Forex-Backtesting-Repo) -- Architektur-
Vorbild `fk_instant_funding/paper_bot.py`: 5 der 6 Scan-Funktionen 1:1 von
dort uebernommen (Gold ASB/CLS Practical/Trend Pullback/CTNL/ORB, dort
bereits validiert), NEU ist nur `_scan_ou_modell` (Bracket-Engine `ou_paper_
backtest/portfolio.py::simulate_bracket_portfolio` auf der TTP-handelbaren
Teilmenge, `ou_paper_backtest/scanner.py::_load_ttp_tradable_tickers`).

Ein gemeinsamer Trade-Log speist ZWEI unabhaengige virtuelle 100k-Konten
(TTP-Paper, IQMarkets-Paper) -- gleiche Trades/gleiche Positionsgroessen-
Formel, aber getrennte Regel-Engines (`check_ttp_rules`/`check_iqmarkets_
rules`: Tageslimit+Gesamt-DD+Ziel vs. nur Gesamt-DD+Ziel). Ende-zu-Ende
verifiziert (2026-08-27): alle 6 Scans laufen fehlerfrei, State bleibt ueber
mehrere Laeufe stabil ohne doppelte Trades, harter 1%-Positionsdeckel nie
wirklich gebraucht (max. beobachteter Wert ~0.32%).

## MT5-Bridge (Funded-Portfolio-Bridge)

`C:\Users\andre\Funded-Portfolio-Bridge\` (ausserhalb des Git-Repos, gleiche
Trennung wie alle anderen MT5-Bridges). Architektur-Vorbild:
`FKInstantFunding-MT5-Bridge/run_once.py` (identisches "kein zweites
Signal-Implementieren"-Prinzip, sys.path-Import aus `challenge_portfolio.
paper_bot`), erweitert um: zwei Konten statt eines, OU-Modell-Bein,
`resolve_symbol()` mit Broker-Suffix-Fallback (`symbol_suffix`).

**Kontenuebernahme (Nutzerentscheid 2026-08-28)**: KEINE neuen Demo-Konten --
uebernimmt dieselben zwei Konten, die aktuell solo von `OU-Modell-MT5-Bridge`
(Konto 2, Login 504072729, TTP-Demo -- **Konto 1/Login 504069845 ist ECHTES
GELD und bleibt in jedem Fall unberuehrt**) und `CTNL-Edge-MT5-Bridge`
(BeyondIQCapital, Login 16054) bespielt werden. Vor Scheduled-Task-Einrichtung
UND vor `DRY_RUN=False` muss der jeweils alte Bot auf diesem Konto pausiert
werden (siehe `Funded-Portfolio-Bridge/README.md`) -- noch NICHT ausgefuehrt.

**Verbindungs-/Symbol-Test (2026-08-29, read-only, keine Order gesendet)**:
beide Konten erreichbar, AutoTrading an. TTP: alle FX/Metalle + OU-Modell-
Stichprobe roh handelbar, Ausnahmen `XPTUSD`->`PLATINUM`, `SP500`->`US500`;
**kein NASDAQ-Index-Symbol auf TTP gefunden** -- ORB-NASDAQ-Bein wird dort
strukturell uebersprungen (SizingError, kein Crash), bis ein Symbol gefunden
wird. IQ Markets/BeyondIQCapital: durchgehend `.gbe`-Suffix, inkl. OU-Modell-
Einzelaktien (`AAPL.gbe` etc.) -- `GOOGL(.gbe)` nicht gefunden, evtl. anderer
Ticker (`GOOG.gbe`?), noch ungeklaert.

**Echte Order-Ausfuehrung implementiert (2026-08-29, Nutzerauftrag)**:
`executor.py` (woertlich GoldASB-MT5-Bridge/CTNL-Edge-MT5-Bridge-Muster) +
`run_once.py` zustandsbehaftetes Positions-Tracking (`bridge_state_<id>.json`,
neues Schema `{"positions", "account_start"}`): neue offene Signale -> echter
Markt-Entry (nur Broker-SL, bewusst KEIN Broker-TP -- Begruendung im Modul-
Docstring, Exit stattdessen ueber denselben Re-Scan-Vergleich, der auch den
Paper-Bot antreibt), bereits getrackte + jetzt geschlossene Signale -> echtes
Schliessen ueber das gespeicherte Ticket. `account_start`-Gating verhindert
faelschliches Nacheroeffnen von Alt-Signalen beim ersten Lauf. End-zu-Ende
mit zurueckdatiertem `account_start` gegen IQ Markets getestet (DRY_RUN): 4
gleichzeitige CTNL-Reversal-Entries korrekt geplant, Exit-Pfad synthetisch
verifiziert. Nebenfund: `sys.stdout`-UTF-8-Reconfigure fehlte in `run_once.py`
(Emoji-Log-Zeilen crashten auf Windows cp1252) -- ergaenzt.

**Offene Punkte** (siehe README.md fuer Details): (1) `DRY_RUN` steht noch auf
`True` -- kein einziger echter Order-Request wurde je gesendet, (2) OU-Modell-
Handelbarkeit auf BeyondIQCapital nur stichprobenartig geprueft (kein
vollstaendiges Aequivalent zu `build_ttp_tradable_universe.py`), (3) Regel-
Engine (Tageslimit/Gesamt-DD/Ziel) laeuft bisher nur im Paper-Bot gegen die
simulierte Equity, nicht in der Bridge gegen die echte Kontohistorie.

**Zwei reale Befunde aus dem ersten vollen DRY_RUN-Testlauf (2026-08-29)**:
1. **Bug (behoben)**: `_scan_ou_modell` importierte `ou_paper_backtest/config.py`
   ueber ein nacktes `import config` -- kollidierte mit der Bridge's eigener
   gleichnamiger `config.py` (bereits in `sys.modules['config']` gecacht,
   bevor `paper_bot` importiert wird), sodass `portfolio.py`s eigenes
   `import config` intern die FALSCHE config bekam (`AttributeError:
   INITIAL_EQUITY`). Betrifft nur den Bridge-Kontext, nicht den Paper-Bot
   solo. Fix: `_import_ou_paper_backtest()` in `challenge_portfolio/
   paper_bot.py` laedt config/portfolio/scanner ueber `importlib` unter
   eindeutigen Namen, mit `sys.modules['config']` nur WAEHREND des Ladens
   temporaer umgebogen, danach restauriert -- isoliert verifiziert (Collision-
   Szenario nachgestellt) UND End-to-End (329 echte Trades produziert).
2. **Struktureller Befund -- behoben (2026-08-29)**: CTNL Reversals
   Risikoanteil (`CAPITAL_WEIGHT` 1/6 x `risk_pct` 0.15% ≈ 0.025% der Konto-
   Equity, bei $100k ≈ $25) lag auf IQ Markets/BeyondIQCapital unter der
   minimalen handelbaren Lot-Groesse fuer Gold (`volume_min=0.01`, Verlust/Lot
   ≈ $5987 bei der beobachteten SL-Distanz -> $25 Risiko ergab nur 0.004
   Lots). Auf Nutzerauftrag geloest via `Funded-Portfolio-Bridge/run_once.py::
   CTNL_MIN_ACCOUNT_SIZE = $300'000` (Positionsgroesse fuer `ctnl_continuation`/
   `ctnl_reversal` rechnet so, als haette das Konto mindestens diese Groesse --
   wirkt nur auf diese zwei Beine) -- live verifiziert, ergibt jetzt 0.01 Lots
   statt 0.0.

**Symbol-Check TTP finalisiert (2026-08-29)**: `XPTUSD`->`PLATINUM`,
`SP500`->`US500`, `NASDAQ`->`USTEC` ("US 100 Index Cash") -- alle drei jetzt
in `Funded-Portfolio-Bridge/config.py`s `symbol_map` fuer TTP eingetragen,
kein NASDAQ-Symbol-Luecke mehr.

**Verknuepfung**: [[gold-ctnl-edge-portfolio]] (BeyondIQCapital-Konto-
Herkunft, IQ-Markets-Regelwerk-Details), [[mt5-haupt-bot-trend-pullback]].
