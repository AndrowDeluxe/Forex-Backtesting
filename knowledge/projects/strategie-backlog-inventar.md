# Project: Strategie-Backlog-Inventar (Second-Brain-Backfill)

**Ziel**: NICHT mehr jeden Strategie-/Analyse-Ordner im Repo erfassen
(ursprünglicher Plan, s.u.) — **Scope am 2026-09-01 vom Nutzer eingegrenzt**:
nur (a) aktuell relevante Projekte/Strategien (= live oder pausiert, aber
mit einem echten Bot/Task in `DASHBOARD.md`s Statustabelle verknüpft) und
(b) Filter/Strategie-Bausteine mit nachgewiesenem, cross-strategy nutzbarem
Mehrwert (z.B. ein Filter, der in mehreren Strategien bestätigt hilft)
bekommen eine volle PARA-Notiz. Reine Recherche-Stubs ohne Dashboard-Bezug
und ohne bestätigten Edge werden NICHT mehr systematisch nachgezogen,
sondern nur bei thematischem Anlass (analog zur OneNote-Bulk-Bremse in
`README.md`).

**Status**: Batch 1 (5 Ordner) abgeschlossen und nach neuem Scope
re-triagiert (s.u.). Kein weiterer Ordner-für-Ordner-Sweep über die
restlichen ~21 Ordner geplant — stattdessen gezielte Prioritätenliste unten.

**Methode je Ordner**: Docstring des Haupt-Engine-/Backtest-Moduls lesen
(im Repo bereits Konvention, jedes Modul beschreibt Quelle/These im
Kopf-Kommentar), git-Log-Datum der letzten Änderung, Check ob in
`app_pages/` verdrahtet (= im Streamlit-Dashboard sichtbar/gepflegt statt
nur Recherche-Code).

## Bereits mit eigener PARA-Notiz abgedeckt (zur Übersicht, nicht neu erfasst)

`bond_yield_indicator`, `challenge_portfolio`, `fk_instant_funding` (Teil),
`ny_open_orb`, `orb_strategy` (referenziert, verworfen), `gold_ctnl_edge`
(Logs-Ordner; Code evtl. in `combined_strategy`/`strategy`), `gold_smc_htf_ltf`
(referenziert, wird als Indikator-Bibliothek von mehreren Strategien
mitgenutzt), `mt5_david_v2`, `mt5_gold_silver_divergenz`, `mt5_trend_pullback`,
`london_range_bos_retest`.

**Lücke gefunden**: `cls_practical` hat KEINE `knowledge/`-Notiz — die
Recherche dazu (adoptiert: 09:00-Checkpoint, Tagesraten-Risk-Scaling;
verworfen: Cross-/Index-Filter, FRED-Zinsen) liegt bisher nur in Claudes
eigenem Memory-System (`cls_practical_strategy_state.md`), nicht
git-versioniert/für andere Sessions sichtbar. Sollte bei Gelegenheit als
eigene `resources/` oder `archive/`-Notiz nachgezogen werden — nicht in
diesem Batch, da vollen Distill braucht, kein reines Inventar.

## Batch 1 (2026-09-01)

| Ordner | These (aus Modul-Docstring) | Im Dashboard verdrahtet? | Letzte Änderung | Einschätzung |
|---|---|---|---|---|
| `asia_ote` | Asia-Range Fibonacci/Premium-Discount-Entries (fib_limit/candle_reaction/range_breakout) auf EURUSD, H1/H4-Trend via `gold_smc_htf_ltf`. Quelle: Chat 2026-08-21. | Nein | 2026-08-27 (Commit-Msg deutet "plus pending work" an) | Unfertiger Recherche-Stand, kein abgeschlossenes Ergebnis sichtbar — Status unklar, evtl. einfach liegengeblieben. Kandidat für Rückfrage statt Auto-Archivierung. |
| `asian_range_breakout` | Gold (XAUUSD) Asian-Range-Breakout, State-Machine nach TradeStation-EasyLanguage-Spec des Nutzers (`Gold_Asian_Breakout_Strategy.txt`, 2026-08-04): OCO Buy-Stop/Sell-Stop an Range-High/-Low, kein TP, Flat-by-Exit. | **Ja** (`app_pages/asian_range_breakout.py`), volle Toolbox: Monte Carlo, Walk-Forward, Sizing, Execution-Overlay, COT/DXY/VIX-Filter | 2026-08-11 | Das ist die Grundlage des (aktuell pausierten) Gold-ASB-Bots aus der Status-Tabelle — **höchste Priorität für vollen Distill**, da Live-Bot-relevant, aber bisher keine PARA-Notiz zur Strategie-These/Backtest-Historie selbst. |
| `auction_playbook` | Rekonstruktion von Fabio Valentinis "Auction Market Playbook" (Value-Area-Breakout → Fail=Mean-Reversion / Hold=Trend-Continuation), auf BTC/Binance (Taker-Volumen als Aggression-Proxy statt echtem Footprint). | Ja (`app_pages/auction_playbook.py`) | 2026-08-27 | Eigenständiges Paper-Rekonstruktions-Projekt, im Dashboard aktiv sichtbar, aber ohne `resources/`-Notiz zur Quelle (Playbook) oder `projects/`-Notiz zum Backtest-Ergebnis. Guter Kandidat für vollen Distill. |
| `btc_ema_cross` | BTC EMA9/21-Cross, 24/7-Krypto (Sonderfall: einzige Strategie, die NICHT der Wochenend-/Spread-Pause unterliegt, siehe CHANGELOG 2026-08-29). | Ja (`app_pages/btc_ema_cross.py` + `btc_ema_cross_live_log.py`) | 2026-08-31 | War LIVE (Binance), laut Dashboard aktuell pausiert. Hat reale Handelshistorie, aber keine PARA-Notiz zur Backtest-These — Lücke trotz Live-Relevanz. |
| `checklist_strategy` | Codifizierte diskretionäre Checklist-Strategie, eigener Multi-Position-Simulator (überlappende Trades erlaubt, anders als `strategy/backtest.py`s one-at-a-time). | Ja (`app_pages/checklist.py`) | 2026-07-29 | Älteste der 5 (kein Aktivitäts-Update seit über einem Monat) — evtl. eher Referenz/Fingerübung als aktiv verfolgte Strategie. Status per Rückfrage klären, bevor voller Distill investiert wird. |

## Re-Triage von Batch 1 nach neuem Scope (2026-09-01)

- **Bleiben im Scope** (Dashboard-Bezug): `asian_range_breakout` (Gold-ASB-Bot),
  `btc_ema_cross` (BTC-EMA-Cross-Bridge/-Scan) — weiterhin Kandidaten für
  vollen Distill.
- **Raus aus dem aktiven Backlog** (kein Dashboard-Bezug, kein bestätigter
  Edge sichtbar): `asia_ote` (unfertiger Stand, "pending work"),
  `checklist_strategy` (>1 Monat keine Aktivität, nie im Dashboard verlinkt
  gewesen). Werden nicht gelöscht/verworfen, nur nicht mehr aktiv
  nachverfolgt — falls sie im Gespräch wieder auftauchen, normaler CODE-Zyklus.
- **Unklar, separat zu bewerten**: `auction_playbook` — eigenständige
  Paper-Rekonstruktion (Fabio Valentini), im Dashboard/Streamlit sichtbar,
  aber kein Live-/Paper-Bot dahinter. Bleibt vorerst offen, ob das unter (a)
  oder (b) fällt — hängt davon ab, ob die Rekonstruktion einen bestätigten
  Edge oder wiederverwendbaren Filter geliefert hat (noch nicht geprüft).

## Neue Prioritätenliste: aktuell relevante Strategien ohne PARA-Notiz

Abgeleitet aus `DASHBOARD.md`s Statustabelle (live oder pausiert, aber mit
echtem Bot/Task) gegen bestehende `projects/`/`archive/`-Notizen abgeglichen:

| Ordner/Thema | Bot/Task in DASHBOARD.md | Hat PARA-Notiz? |
|---|---|---|
| `asian_range_breakout` (Gold ASB) | Gold-ASB-Scan/GoldASB-MT5-Bridge, Bein von Funded-Portfolio-Bridge | **Nein — Lücke** |
| `cls_practical` | CLS-Practical-Bridge/-Scan, Bein von Funded-Portfolio-Bridge | **Nein — nur in Claude-Memory, s.o.** |
| `btc_ema_cross` | BTC-EMA-Cross-Bridge/-Scan | **Nein — Lücke** |
| `ek_portfolio` | EK-Portfolio-Bridge (**live, echtes Geld**) | **Nein — Lücke, trotz Live-Echtgeld-Bot** |
| OU-Modell (`ou_paper_backtest`/`ou_modell_logs`) | OU-Modell-MT5-Bridge/-ScannerHourly (live-Scanner) | **Nein — Lücke** |
| `gold_ctnl_edge` | CTNL-Edge-MT5-Bridge (abgelöst durch Funded-Portfolio-Bridge) | Ja (`gold-ctnl-edge-portfolio.md`) |
| `mt5_trend_pullback`, `mt5_gold_silver_divergenz` | Beine von Funded-Portfolio-Bridge | Ja |
| `ny_open_orb` | Beine von Funded-Portfolio-Bridge | Ja |
| `challenge_portfolio` / `fk_instant_funding` | eigene Bots | Ja |

**Fünf echte Lücken bei aktuell laufenden/pausierten Strategien**:
`asian_range_breakout`, `cls_practical`, `btc_ema_cross`, `ek_portfolio`,
OU-Modell. Das ist die eigentliche Prioritätenliste für die nächsten vollen
Distills — deutlich kürzer als die ursprünglichen ~21 restlichen Ordner.

## Zweite Achse: Filter/Bausteine mit echtem Mehrwert (noch nicht erfasst)

Noch nicht als eigene `resources/`-Notiz destilliert, obwohl mehrfach
bestätigt/cross-strategy relevant: EMA-Ribbon-Bias "neutral" (hilft SP500/
US30-ORB, schadet NASDAQ — `strategy/mtf_ema_ribbon.py`), Long-only-Bias auf
US-Indizes (unabhängig in `orb_strategy` UND `ny_open_orb` bestätigt),
0.6x-ATR-Stop als wiederkehrend bester Wert (SP500-Feingrid UND NASDAQ),
COT/DXY/VIX/CLS-Settle-Filter aus `asian_range_breakout`. Noch nicht
bewertet, ob sich daraus eine eigene `resources/`-Notiz lohnt oder ob es
besser bei den jeweiligen Projekt-Notizen bleibt — Rückfrage bei Bedarf.

**Nächster Schritt**: die 5 Lücken oben nacheinander (nicht alle 5 auf
einmal) voll distillen, beginnend mit `asian_range_breakout` (höchste
Priorität: Live-Bot-Grundlage) — auf Zuruf.
