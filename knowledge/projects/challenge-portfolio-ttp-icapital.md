# Project: Challenge-Portfolio (TTP + IQ Markets/"I Capital")

**Ziel**: Das bereits validierte Multi-Strategie-Portfolio (Gold ASB, CLS
Practical, Trend Pullback, CTNL Edge, OU-Modell, NY-Open ORB) als
Paper-Forward-Test auf zwei virtuellen 100k-Konten mobilisieren -- eines je
Ziel-Regelwerk. "I Capital" im Nutzer-Wortlaut = IQ Markets/BeyondIQCapital
(identische Zahlen: Positionslimit 1%, Gesamt-DD 6%, Ziel 8% -- bereits das
reale Konto `IQCEV100K-130835` aus [[gold-ctnl-edge-portfolio]]).

**Status**: Paper-Forward-Test-Bot gebaut und verifiziert (2026-08-27), noch
KEIN Scheduled Task aktiv, keine echten Konten betroffen. Getrennt von den
bereits live laufenden Solo-Bots (OU-Modell auf den echten TTP-Konten
konto1_ttp/konto2_ttp, CTNL Edge auf dem echten IQ-Markets-Konto) -- ruehrt
an deren Order-Ausfuehrung nicht an.

## Regelwerke

- **TTP**: Tageslimit -3% (Tages-Reset), Gesamt-Drawdown -7% (harter
  Kill-Switch), Ziel +10%.
- **IQ Markets**: kein Tageslimit, Gesamt-Drawdown -6% (harter Kill-Switch),
  Ziel +8%. Positionslimit 1% strukturell durch die Kapitalanteil-Verduennung
  erfuellt (max. Einzel-Trade-Risiko in der Simulation lag bei ~0,32% des
  Startkapitals, klar unter der 1%-Grenze).

## Roster & Analyse (2026-08-27)

Frisch aktualisiert gegenueber der bisherigen FK-Portfolio-Analyse in
`app_pages/portfolio_construction.py` (Tab "FK-Portfolio", dort 4-5 Beine
OHNE ORB): auf Nutzerwunsch **NY-Open ORB als 6. Bein aufgenommen** --
bisher bewusst ausgeschlossen ("keine Evidenz, dass TTP/IQ Markets die
Instrumente anbieten"), das Broker-Verfuegbarkeitsrisiko wird jetzt in Kauf
genommen (vor echtem Livegang zu pruefen).

Skript: `scripts/research_challenge_portfolio_6leg.py`, Ergebnis:
`portfolio_construction/results/challenge_portfolio_6leg.json`. Vergleich
5-Bein-Baseline vs. 6-Bein mit ORB (Block-Bootstrap Monte Carlo, block_size=20,
n_sims=3000, gemeinsames Fenster 2024-08-02 bis 2026-07-29, ~2 Jahre, begrenzt
durch CTNL Edges kurze Historie):

| | 5 Beine (Baseline) | 6 Beine (mit ORB) |
|---|---|---|
| CAGR | 13.9% | 15.6% |
| MaxDD | -4.5% | -3.9% |
| TTP p_breach / p_target / median Tage | 1.6% / 98.4% / 168 | 0.2% / 99.8% / 153 |
| IQ Markets p_breach / p_target / median Tage | 3.2% / 96.8% / 131 | 0.9% / 99.1% / 123 |

ORB verbessert **alle** Kennzahlen gleichzeitig auf **beiden** Regelwerken
(hoehere Rendite, niedrigerer Drawdown, niedrigere Bruchwahrscheinlichkeit,
schneller zum Ziel) -- Korrelation zu den 5 bestehenden Beinen liegt zwischen
-0.07 und +0.03 (praktisch unkorreliert, Index-Opening-Range-Breakouts sind
strukturell verschieden von FX/Gold/Krypto/Aktien-Strategien). Klarer,
eindeutiger Fall fuer die Aufnahme.

**Wichtiger Datenhinweis**: der ORB-Beitrag in dieser Analyse stammt NICHT aus
der aelteren `legs/orb_strategy_r100.csv` (Stand 2026-08-19, aus der
mittlerweile verworfenen alten `orb_strategy/`-Variante, siehe
[[ny-open-orb-sp500]]), sondern frisch aus den drei aktuellen
per-Instrument-Trade-Listen (`legs/trades_ny_orb_{sp500,us30,nasdaq}.csv`,
1:1 aus dem aktuellen `ny_open_orb/`-Modul, dieselbe Config wie
`app_pages/ny_open_orb_portfolio.py`).

OU-Modell nutzt fuer DIESE Portfolio-Kombinationsanalyse bewusst den
Referenz-Risiko-Ersatz (volles Universum, `legs/ou_modell.csv`) statt der
echten TTP-58-Ticker-Teilmenge (`ou_modell_fk_r150.csv` endet 2024-12-31, zu
kurz fuer ein gemeinsames Fenster mit CTNL ab 2024-08) -- derselbe, bereits in
`ctnl_fk_extension.json` dokumentierte Kompromiss. Der Paper-Bot selbst
scannt live die ECHTE TTP-handelbare Teilmenge (siehe unten).

## Paper-Bot (`challenge_portfolio/`)

Architektur 1:1 nach Vorbild `fk_instant_funding/paper_bot.py`. Ein Scan pro
Strategie versorgt EINEN gemeinsamen Trade-Log/Equity-Verlauf (beide Konten
sehen dieselben Trades + dieselbe Kapitalanteil-Verduennungsformel, nur die
Regel-Auswertung unterscheidet sich je Zielfirma):

- **5 Beine 1:1 aus `fk_instant_funding/paper_bot.py` uebernommen** (bereits
  validiert): Gold ASB, CLS Practical, Trend Pullback, CTNL Edge
  (Continuation+Reversal), NY-Open ORB (SP500+US30+NASDAQ).
- **Neu**: `_scan_ou_modell()` -- Bracket-Exit-Engine
  (`ou_paper_backtest/portfolio.py::simulate_bracket_portfolio`) auf der
  echten TTP-handelbaren Teilmenge (SP500+Nasdaq100 via
  `ou_paper_backtest/scanner.py::_load_ttp_tradable_tickers`, DAX raus -- 0
  Ticker dort handelbar), Config stop_sigma=3.0/be_trigger_r=0.25/kein TP
  ("gesperrte Baseline" aus `oos_holdout_challenge_profiles.py`).
- Risikostufen (`LEG_RISK_PCT`, identisch fuer beide Konten): Gold ASB 2,0%,
  CLS Practical 1,5%, Trend Pullback 0,5%, CTNL Continuation 0,5%/Reversal
  0,15%, OU-Modell 1,0%, ORB kombiniert 1,0% (1/3 je Instrument).
  `CAPITAL_WEIGHT = 1/6`. Hard-Cap 1% des Startkapitals pro Trade (erfuellt
  IQ Markets' Positionslimit strukturell -- in der Verifikation lag der
  tatsaechliche Maximalwert bei ~0,32%, der Cap griff nie).
- Zwei Regel-Checks (`check_ttp_rules`, `check_iqmarkets_rules`) auf demselben
  Equity-Verlauf, siehe Tabelle oben fuer die Schwellen.

**Verifiziert (2026-08-27)**: alle 6 Signal-Scans laufen fehlerfrei durch
(inkl. neuem OU-Modell-Scan), State-Persistenz/Dedup ueber mehrere Laeufe
stabil (keine doppelten Trades), Positionsgroessen-Cap nie verletzt.

**Noch offen**: `scripts/challenge_portfolio_task.ps1` existiert, ist aber
NICHT in Task Scheduler eingerichtet (bewusste, separate Nutzer-Entscheidung,
gleiches Vorgehen wie beim CTNL-FK-Scan-Task). Vor echtem Livegang: Broker-
Verfuegbarkeit von SP500/US30/NASDAQ-CFDs auf TTP/IQ Markets pruefen (offener
Punkt aus der ORB-Integration in `fk_instant_funding_final.json`).

**Verknuepfung**: [[gold-ctnl-edge-portfolio]] (IQ-Markets/BeyondIQCapital-
Konto-Details), [[mt5-haupt-bot-trend-pullback]], [[ny-open-orb-sp500]].
