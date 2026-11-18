# Project: Automatisierte Aktienanalyse + Aktienbot

**Ziel**: Eine automatisierte Aktienanalyse ähnlich der KI von Investing.com (Fair Value,
Kennzahlen-Scoring, News-/Earnings-Zusammenfassung), aber nachprüfbar statt Blackbox. Darauf aufbauend
später ein Aktienbot mit Ausführung.

**Status**: **Aktiv seit 2026-11-15, Teil des Dachprojekts** [[quant-diskretionaer-fusion]]
(Nutzerentscheid 15.11., vorher „geparkt bis die Makro-Basis steht“; der Makro-Agent läuft inzwischen).
Auslöser: Prosper-AI-Kurs „Grok Trading Team“ ([[prosper-bot-trendregel-echtdaten]]) und eine
NVIDIA-Handanalyse am 15.11. Stufe 1 (Screener + Forward-Ledger + Dashboard) gebaut. **Forward-Test seit
15.11.2026** (Version 1.0, alle Annahmen vom Nutzer bestätigt). Jeder Lauf wird in `fusion_lab/screener/archive/`
protokolliert und committet.

**Woher die Werte kommen:** Gewichte, ATR-Abstände und CRV ≥ 2 sind gängige Startwerte (gleich gewichtet =
neutral), 65/35 ist Nutzerwunsch. Nichts davon ist getestet. Backtestbar sind die Preiszonen und die Kurs-Teile
des Scores (Survivorship-Bias der heutigen Indexliste beachten); Fundamentaldaten nur mit SEC-EDGAR-Historie;
News/Analystenziele nur vorwärts. Backtest der prüfbaren Teile läuft parallel, Ergebnisse höchstens als Version 1.1.

## Stufe 1: täglicher Aktien- + Krypto-Screener (gebaut 15.11.2026)

Code `fusion_lab/screener/`, Dashboard `fusion_lab/dashboard/`, Tests `tests/test_screener.py` (20).

- **Universum:** S&P 500 + Nasdaq-100 (518 Ticker, entdupliziert) + Watchlist (NVDA); Krypto Top 30 nach
  Marktkapitalisierung mit Binance-USDT-Paar, ohne Stablecoins/Gold-/Wrapped-Token.
- **Daten (alle frei):** yfinance (Kurse, Fundamentaldaten, Analystenziele, Termine), Binance (Kerzen,
  Funding), CoinGecko (Marktdaten), alternative.me (Fear & Greed), Google-News-RSS (Schlagzeilen).
- **Score 0–100** aus Querschnitts-Perzentilen, Gewichte vorab festgelegt (`config.py`). Signal im
  Prosper-Stil nach Nutzerwunsch: **≥ 65 KAUFEN, ≤ 35 VERKAUFEN**. Tiefen-Kandidaten (Top 10 + Watchlist
  bzw. Top 5 + BTC/ETH): 70 % Kennzahlen + 30 % News-Stimmung.
- **Preisbereiche deterministisch** (`levels.py`): Swing-Marken, SMAs, Volumenprofil, Kurslücken, ATR →
  A Rücksetzer-Zone (Limit), B Ausbruch (Stop), C Abwarten; nur Chance-Risiko ≥ 2.
- **LLM** (`claude.exe -p`, Abo, Sonnet): ordnet Schlagzeilen ein (−2…+2), Pro/Contra, wählt A/B/C. Nennt
  keine eigenen Preise; der Validator prüft Dollar-Beträge gegen das Faktenpaket. ~12 s je Titel.
- **Ausgabe:** Markdown/JSON-Bericht, Telegram-Kurzfassung, Notion-Seiten „📈 Aktien-Screener“ /
  „🪙 Krypto-Screener“, Dashboard (Cloudflare Pages + Access, Einrichtung `fusion_lab/dashboard/README.md`).
- **Forward-Ledger** `fusion_lab/screener/ledger/ledger.csv`, Regeln `ledger/FORWARD.md`. Erfolg nur, wenn
  KAUFEN **Universum und Benchmark** schlägt (Kontrolle gegen Long-Beta).
- **Tasks:** `Forex-Screener-Aktien` Mo–Fr 23:00, `Forex-Screener-Krypto` täglich 07:45.
- **Referenzfall:** NVDA-Handanalyse 15.11. (A 149–158 / B > 172) im Ledger. Folge-Analyse nach den
  Q3-Zahlen per Telegram am 17.11., 23:45 (`Forex-NVDA-Earnings-Analyse`, einmalig).

## Rohstoffe (gebaut 18.11.2026)

Auslöser: Kupfer-Analyse vom 18.11. mit 5 Recherche-Agenten (`fusion_lab/screener/archive/kupfer_analyse_2026-11-18.md`).
Nutzerentscheid: Kern-10 (Gold, Silber, Platin, Kupfer, WTI, Brent, Erdgas, Weizen, Mais, Soja), zwei Stufen, Signale +
Ledger, Mo–Fr 23:15.

- **Täglich** `python -m fusion_lab.screener rohstoffe` (`data_commodities.py`, `scoring.commodities`,
  `pipeline.run_commodities`): Yahoo-Futures + CFTC-COT; Score absolut (Trend 30, Momentum 25, rel. Stärke gg. DBC 15,
  COT contrarian 20, 52-W-Lage 10); alle zehn mit Szenarien A/B/C und News-LLM; eigenes Ledger, Probebetrieb.
- **Wöchentlich** `scripts/commodity_deep_task.ps1` (So 18:00): je Rohstoff `claude.exe -p` mit Web, Prompt
  `scripts/reports/commodity_deep_prompt.md` + Branchen-Checkliste aus `scripts/reports/commodity_deep.py`, Ausgabe
  `fusion_lab/screener/archive/rohstoffe_tief/`.
- **Cockpit:** Tab „Rohstoffe“, KPIs Gold/WTI/Kupfer in der Übersicht, Wochenanalyse aufklappbar.
- 18.11.: Version 1.1 (COT-Gewicht 0), Wochenanalyse nur Gold/Silber/Kupfer (Nutzerentscheide).
- Backtest der Bausteine für Edelmetalle auf 4–26 Wochen: kein Baustein trägt, keine Variante schlägt „immer long“, Shorts verlieren OOS → [[edelmetalle-htf-makro]].

## Bekannte Grenzen

- Yahoo-Fundamentaldaten sind nicht historisch → kein ehrlicher Backtest des Scores, nur Forward.
- Erster Lauf 15.11.: Energie-Titel (EOG, APA, CVX, COP) weit oben, weil Trend + Bewertung + Wachstum
  zusammen stark sind. Ob das Sektor-Klumpen erzeugt, zeigt der Forward-Test.

## Später (nicht gebaut)

- Grok/X als Zusatzquelle für Sentiment (kostenpflichtig), erst wenn der Forward-Test zeigt, dass
  Stimmung etwas beiträgt.
- Ausführung: Alpaca Paper-Trading (offizieller MCP-Server `alpacahq/alpaca-mcp-server`, siehe
  [[agentisches-research-system-und-self-learning-bot]]), gleiche Freigabe-Gates (3 Stufen) wie im
  Dachprojekt. Erst nach bestandenem Forward-Test.
- Anthropic-Finanz-Connectors (S&P Capital IQ, FactSet, Morningstar) sind kostenpflichtig und nicht
  verbunden.
