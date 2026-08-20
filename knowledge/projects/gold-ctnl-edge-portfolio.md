# Project: Gold CTNL Edge Portfolio (Continuation + Reversal-Kaskade)

**Ziel**: Zwei SMC-basierte Gold-Intraday-Strategien (H4-Struktur ->
H1-Bestaetigung -> LTF-Entry) einzeln validieren, zu einem Portfolio
kombinieren und Risk-Sizing fuer zwei Szenarien festlegen: FK Challenge
(IQ Markets, max 6% DD, max 1%/Position, Ziel +8%) und EK (eigenes Konto,
renditeoptimiert). Ursprung: eigene TradingView-Chartbeispiele des
Nutzers (nicht SSRN-Paper-Pipeline -- daher separat von
[[gold-ssrn-strategie-auswertung]] und nicht in dessen
`checklist_state.json` getrackt).

**Status**: Phase 6 (Robustheit) abgeschlossen, Befund gemischt -- siehe
unten. Realisierung (Streamlit-Page-Update, finale FK/EK-Parameter)
laeuft.

**Prozess-Referenz**: `app_pages/education_gold_intraday.py`, Phase 6
"Robustheit" -- p6_1 Walk-Forward/echter OOS-Split, p6_2 Monte-Carlo-
Bootstrap (Muster `ou_paper_backtest/monte_carlo.py`), p6_3 Kosten-
Sensitivitaet, p6_4 mehrere Jahre/Regime. **Wichtige Lektion (chat
2026-08-20)**: dieser Prozess wurde die ganze Session ueber NICHT
befolgt -- IS/OOS-Split lag durchgehend nur innerhalb von 2024-08/2026-08,
Phase 6 wurde erst nachtraeglich (auf Nutzer-Nachfrage) nachgeholt, und
dabei zunaechst ein Ad-hoc-Bootstrap gebaut statt das etablierte
`ou_paper_backtest/monte_carlo.py` wiederzuverwenden. Fuer kuenftige
Strategie-Arbeit: Phase 6 IMMER vor Portfolio-Bau/Risk-Sizing abschliessen,
nicht danach.

## Finale, gesperrte Configs

**Continuation** (`gold_smc_htf_ltf/continuation.py::run_pipeline`,
Einzelposition): `trend_indicator="ema_adx_combo"` (M15), `htf_valid_bars=24`,
`entry_variant="direct"` (M5-Sweep-and-Reject), `min_target_distance_atr=0.5`.
BacktestConfig: `stop_atr_mult=0.5`, `use_vwap_target=True` (H4-Level-TP),
`max_hold_bars=288` (24h auf M5).

**Reversal-Kaskade** (`gold_smc_htf_ltf/reversal_cascade.py::run_pipeline`
+ `concurrent_backtest.py` fuer Re-Entry): `h4_confirm_bars=30`,
`h1_valid_bars=24`, `require_ema_reject=True`, `m15_entry_mode="repeat_sweep"`.
BacktestConfig: `stop_atr_mult=3.0`, `take_profit_r=5.0`, `max_hold_bars=384`
(96h auf M15 -- NICHT 96 Bars, das war ein Transkriptionsfehler in einer
frueheren Session-Zusammenfassung). Re-Entry: `max_concurrent=3`.

LTF-Entry ist bei BEIDEN M5? Nein -- Continuation nutzt M5, Reversal-
Kaskade nutzt M15 (H4->H1->M15-Kaskade, direkt aus des Nutzers eigener
Chart-Beschreibung vom 2026-08-18 abgeleitet). M5-Entry fuer die
Reversal-Kaskade wurde explizit getestet (`research_gold_smc_reversal_
m5_entry.py`) und schlaegt M15 NICHT -- repeat_sweep auf M5 hat 10.819
Rohsignale statt 3258 auf M15, das Muster degeneriert auf M5 zu
Mikro-Rauschen statt eines echten Wiedertest-Events.

## Phase 6 -- Robustheit: Befunde

**p6_1/p6_4 Walk-Forward (2016-01 bis 2024-08, nie gesehen)**:
NEGATIV in allen 4 Sub-Perioden. Continuation Sharpe -0.93 bis -2.00,
Reversal-Kaskade -0.46 bis +0.13 (PF meist <1). Buy&Hold schlaegt beide
in 3 von 4 Fenstern. Das 2024-08/2026-08-Fenster (Sharpe 1.33/1.07 in
derselben Baseline-Messung) ist der einzige durchweg positive Zeitraum.

**p6_2 Monte-Carlo-Bootstrap** (echtes `ou_paper_backtest/monte_carlo.py`,
block_size=20, n_sims=2000, auf OOS 2025-08/2026-08): FK (0.50%/0.15%)
P(MaxDD>6%)=7.8%, Median Sharpe 2.02. EK (2.00%/1.50%) natuerlich
P(MaxDD>6%)=100% (kein Limit intendiert), Median Sharpe 2.42.

**p6_3 Kosten-Sensitivitaet**: Breakeven-Spread fuer BEIDE Strategien bei
ca. 32-40bps (angenommen: 8bps) -- 5-facher Sicherheitspuffer, unkritisch.

## Regime-Untersuchung (chat 2026-08-20)

Frage: warum funktioniert die Strategie in 2024-26, aber nicht davor?
Makro-Recherche: Zentralbanken kauften 2022-24 durchgehend >1.000t/Jahr
(vs. 473t Schnitt 2010-2021), ausgeloest u.a. durch Russland-Sanktionen
2022 und De-Dollarisierung (USD-Reserveanteil 72%->58%). Erklaert die
Zeitgrenze aber NICHT sauber -- 2022-24 war bereits Rekordkaeufe-Fenster,
performte im Walk-Forward trotzdem negativ.

Datengetriebener Test (ADX(D1)-Trendstaerke, Naehe zum rollierenden
2-Jahres-Hoch, einzeln und kombiniert als Vor-Trade-Filter): **negativ**.
Keine der Schwellen trennt die verlierenden Perioden von der gewinnenden.
Median-ADX liegt in JEDER Sub-Periode zwischen 22-25, auch 2024-26 sticht
nicht heraus. Gefiltert auf die trendstaerksten/hoechsten Tage bleibt
Continuation in 2016-2024 durchgehend negativ.

**Runde 2** (chat 2026-08-20, weitere Makrofaktoren auf Nutzer-Vorschlag:
Krieg, Trump-Regime, VIX, Oel, DXY, Gold-ETF-Inflows): VIX/DXY/Oel via FRED
(`VIXCLS`, `DTWEXBGS`, `DCOILWTICO`) ebenfalls getestet -- ebenfalls
NEGATIV. VIX 2024-26 (median 17.3) liegt im Mittelfeld, nicht auffaellig.
DXY-Niveau ist 2022-24 und 2024-26 praktisch identisch (121.2 vs. 121.0)
trotz gegensaetzlicher Strategie-Performance. Gold-DXY-Korrelation bleibt
ueber alle 5 Perioden konstant schwach (-0.04 bis +0.06). Ein DXY-
Abwertungstrend-Filter (60-Tage-RoC<0) trennt die Perioden ebenso wenig.
"Krieg"/"Trump-Regime" haben keine saubere taegliche Datenquelle im Repo;
Trumps Amtsantritt (2025-01-20) liegt zeitlich 5,5 Monate NACH Beginn des
guten Fensters (2024-08), passt also nicht als Erklaerung. Gold-ETF-
Inflows (World Gold Council) nicht ueber FRED verfuegbar -- Datenluecke.

**Fazit nach 2 Testrunden / 8 Variablen**: kein vorhersagender Regimefilter
gefunden. Weitere Variablen suchen, bis zufaellig eine "passt", waere
selbst eine Form von Overfitting -- Suche hier bewusst beendet.

**Cross-Market-Check (chat 2026-08-21)**: finale, gesperrte Configs
unveraendert auf die G8-Majors (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD,
USDCAD) angewendet, selber Zeitraum wie Gold (2024-08/2026-08), inkl.
IS/OOS-Split. Ergebnis EINDEUTIG NEGATIV: Continuation Sharpe negativ in
allen 6 Paaren x 3 Fenstern (Voll/IS/OOS) ohne Ausnahme (-1.24 bis -3.38).
Reversal-Kaskade in 10 von 12 IS/OOS-Faellen negativ, nur EURUSD-IS
(+0.44) und USDCAD-OOS (+0.46) schwach positiv, keins davon in beiden
Fenstern desselben Paares bestaetigt. Das ist ein STAERKERES Warnsignal
als der reine Walk-Forward-Befund: waere der Edge ein echter struktureller
Mechanismus, sollte er auf mindestens einigen FX-Paaren im SELBEN Zeitraum
zumindest schwach durchschlagen. Stattdessen durchgehend negativ ueberall.
Zusammen mit dem Walk-Forward-Befund spricht das dafuer, dass der Edge
nicht "Gold als Asset" und nicht "dieses SMC-Muster generell" ist, sondern
spezifisch an Golds aussergewoehnlichen 2024-26-Lauf gebunden - eine enge
Kombination, keine breite/robuste Eigenschaft. Skript: `scripts/
research_gold_smc_g8_majors_crossmarket.py`.

**Entscheidung** (Nutzer, 2026-08-20): Strategie NICHT verwerfen -- "die
Vergangenheit ist vergangen, aber die Zukunft kommt noch". Da kein
prognostischer Regimefilter gefunden wurde, stattdessen ein
**Realized-Performance-Kill-Switch**: rollierende Live-Sharpe gegen die
p6_2-Monte-Carlo-Baender pruefen (z.B. Pause/Re-Investigation, wenn
rollierende 90-Tage-Sharpe unter das P5-Band faellt) statt eines
Vorab-Filters, der nachweislich nicht funktioniert.

## Risk-Sizing (finale Entscheidung)

- **FK Challenge (IQ Markets)**: `risk_cont=0.50%`, `risk_rev=0.15%`.
  Bootstrap-Median MaxDD -3.5%, TotalReturn +25%, P(MaxDD>6%)=7.8%.
  Ursprbuenglich gewaehlter 1.00%/0.25%-Pick verworfen, nachdem der
  Bootstrap P(Bruch)=49.7% zeigte (Punktschaetzung aus EINEM historischen
  Pfad war irrefuehrend optimistisch).
- **EK**: `risk_cont=2.00%`, `risk_rev=1.50%`. Median TotalReturn +204%,
  Median MaxDD -20.4% -- deutlich aggressiver, kein hartes DD-Limit.

**Verknuepfung**: [[paper-verarbeitung]] (verwandter Prozess, hier aber
Chart-Ursprung statt Paper), `app_pages/gold_ctnl_edge.py` (Streamlit-
Page, auf finale Configs aktualisiert 2026-08-20).

## Live-Infrastruktur (chat 2026-08-20)

- `gold_smc_htf_ltf/live_signal.py` (dieses Repo): reine Signal-Funktionen,
  90-Tage-Trailing-Fenster, gegen Vollhistorie verifiziert (`scripts/
  verify_gold_ctnl_edge_live_signal.py`, 151/151 Treffer je Strategie).
- `gold_smc_htf_ltf/paper_bot.py` (dieses Repo): FK-Paper-Forward-Test,
  Telegram, stuendlicher Heartbeat, Kill-Switch gegen die Phase-6-Monte-
  Carlo-P5-Schwelle. Scheduled-Task-Wrapper: `scripts/gold_ctnl_edge_fk_
  scan_task.ps1` (noch nicht in Task Scheduler eingerichtet).
- `C:\Users\andre\CTNL-Edge-MT5-Bridge\` (separates, eigenstaendiges
  Projekt, KEIN Git-Repo - gleiches Muster wie GoldASB-MT5-Bridge/
  OU-Modell-MT5-Bridge): die echte Order-Ausfuehrung fuer die FK-Challenge.
  `DRY_RUN=True` per Default. Config-Platzhalter noch NICHT ausgefuellt
  (Terminal FK1 vs. FK2, echter Login/Passwort/Server, Telegram) - siehe
  dortige README.md fuer die vollstaendige Go-Live-Checkliste. Continuation
  bekommt bewusst KEINEN Broker-TP (Ziel ist dynamisch, wird pro Poll
  gegen den aktuellen H1-Target-Wert geprueft); Reversal-Kaskade nutzt
  einen normalen Broker-Bracket (festes 5R-Ziel).
- **EK/MT4**: noch nicht begonnen - kein bestehendes Repo-Muster fuer
  MQL4-EAs, eigene Baustelle.

**Update 2026-08-21**: FK-Bridge scharfgestellt (`DRY_RUN=False`) auf
expliziten Nutzer-Auftrag ("Stelle scharf"), Task Scheduler laeuft alle
5 Min. Terminal-Setup brauchte laengere Fehlersuche: ein einzelner
`mt5.initialize(login=..., password=..., server=...)`-Aufruf blieb
zuverlaessig im IPC-Timeout haengen (Terminal versuchte intern den
FALSCHEN Server); Fix war ein zweistufiger Connect (`initialize()` dann
separat `login()`, mit Retry) - jetzt in `executor.py::connect()`
verankert. Terminal heisst "MT5 Terminal - GoldFKBot" (nicht "...CTNLEdge...",
dieser Pfadname blieb nach vielen fehlgeschlagenen Versuchen dauerhaft
blockiert). Konto: BeyondIQCapital Demo-Challenge IQCEV100K-130835,
Login 16054, Symbol XAUUSD.gbe.
