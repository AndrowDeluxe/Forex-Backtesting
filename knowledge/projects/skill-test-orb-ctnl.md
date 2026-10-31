# Skill-Test: Trading-Skills über ORB + CTNL (28.10.2026)

**Frage:** Was bringen die installierten tradermonty-Skills für unsere zwei
Problem-Edges? Geprüft wurden Diagnose, Filter-Ideen und echte Fills.
**Status:** abgeschlossen. Zwei Filter sind eingefroren und warten auf den
Forward-Test (02.11.2026–31.03.2027). Live wurde nichts geändert.
**Code:** `skill_test/` (`common.py`, `filters.py`), Ergebnisse in `skill_test/results/`.
**Plan:** Overfitting-Sperre ([[overfitting-sperre]]). Gerechnet wurde nur auf IS, jede
Variante ist gezählt.

> **Korrektur 30.10.:** Die ORB-Zahlen unten stammen aus der TTP-Liste vom 04.10. ohne
> NASDAQ-Storno. Mit Storno (`skill_test/results/orb_ctnl_ttp_storno.csv`): ORB-H1 auf IS
> Ø R 0,56 → 0,91, PF 2,25, DD 31 → 17 %, p 0,013; je Bein SP500 0,69 → 1,57, US30 0,48 → 0,80,
> **NASDAQ nur 0,53 → 0,55**. Die anderen Filter wurden nicht neu gerechnet. Der Deckel
> der EK-Bridge für CTNL ist 1, die Überschreitungen liegen alle vor dem 01.10.

## Sperren

| Sperre | IS | Versuche | Eingefroren | Forward |
|---|---|---|---|---|
| `orb_skill_filter_20261028` | 2019–2022 | 13 (5 Filter + 8 Merkmale) | ORB-H1 | bis 31.03.2027, min. 150 Trades |
| `ctnl_skill_filter_20261028` | 2019-01 bis 2024-07 | 14 (6 Filter + 8 Merkmale) | News-Tag-Filter | bis 31.03.2027, min. 40 Trades |

OOS und Tresor sind bei beiden gesperrt (`skip_oos`), weil die alten Sperren sie schon
geöffnet haben. Zur Einordnung: `ny_open_orb_is_reopt_7p` hat zusätzlich 7.560 Versuche.

## Ergebnis je Skill

| Skill | ORB | CTNL | Nutzen |
|---|---|---|---|
| `backtest-expert` | 50/100, REJECT: DD 54 % bei 1 % je Bein, nur 4 Jahre | 68/100, REFINE | bringt was als schneller Gesamtcheck, sieht die 7.560 Versuche aber nicht |
| `edge-strategy-reviewer` | REVISE 83; Bias offen: Lookahead, Auswahl nach Ergebnis | REVISE 80; zusätzlich offen: Versuche nie gezählt, kein Walk-Forward | **die Bias-Checkliste (13 Punkte) bringt was**, der Rest ist eine Schlüsselwort-Heuristik für US-Aktien (Volumenfilter) |
| `trade-hypothesis-ideator` | 4 Karten, 1 × pursue | 4 Karten, 2 × pursue | bringt Struktur (Kill-Kriterien, Experiment). Der Rang ist nur der Mittelwert meiner eigenen Punkte |
| `strategy-pivot-designer` | Stagnation erkannt (Kosten, Tail-Risiko), 3 Pivots: Paar-Handel, Pullback, Fade am Open | – | bringt wenig, die Vorlagen sind generisch. Ideen stehen in der Ideen-Inbox |
| `residual-edge-analyzer` | siehe [[residual-edge-check]] | dito | bringt was |
| `market-breadth-analyzer` | Score < 40 aussetzen: Ø R 0,44 → 0,35 (schlechter) | – | bringt nichts. **Die Daten haben Lookahead:** `Is_Peak`/`Is_Trough` sind nachträglich gesetzt, darum habe ich ohne diese Komponenten gerechnet |
| `uptrend-analyzer` | nicht rechenbar, Daten erst ab 08/2023 | – | – |
| `ibd-distribution-day-monitor` | HIGH/SEVERE aussetzen: Ø R → 0,01 (zerstört den Edge) | – | Die Standardschwellen schlagen an 57 % der Tage an. Umgekehrt gelesen: ORB verdient **in** Verteilungsphasen |
| `market-top-detector` | nicht rechenbar: braucht Leader-Aktien über FMP, Free-Tier zu klein | – | – |
| `economic-calendar-fetcher` | FMP-Kalender kostet (402). Ersatz FRED lokal: +0,02 R | Ersatz FRED lokal: **+0,36 R, p 0,003** | bei CTNL bringt es was. **Eingefroren** |
| `cot-contrarian-detector` | – | FMP-COT kostet (402). Ersatz CFTC: −0,12 R | bringt nichts (nur 13 Tage crowded) |
| `macro-regime-detector` | – | Contraction aussetzen: +0,12 R, p 0,09 | nicht belastbar |
| `drawdown-circuit-breaker` | +0,05 R, DD 54 → 35 % | +0,02 R | dämpft das Risiko, liefert aber keinen eigenen Ertrag |
| `trade-performance-coach` | COOL_DOWN: 10 Verluste in Folge, Risiko 0,5 R im Plan | COOL_DOWN: **47× geplantes Risiko**, 12 Verluste in Folge | bestätigt den bekannten Mindestlot-Effekt (Memory „EK: Mindestlot kehrt die Risiko-Hierarchie um“) |
| `weekly-performance-digest` | 34 Trades, 15 % Treffer | 26 Trades, 19 % Treffer | Live 09/10 gesamt PF 0,53, −311 €. Bringt kaum mehr als ein Pivot |
| `signal-postmortem` | nicht anwendbar | dito | gebaut für Aktien-Screener mit 5- bis 20-Tage-Fenstern |

## Die zwei eingefrorenen Filter

1. **ORB-H1: nur einsteigen, wenn der eigene Index über die letzten 20 Tage gefallen ist.**
   - IS: Ø R 0,76 statt 0,44, PF 1,95, DD 25 statt 54 %, 460 von 1.205 Trades.
   - Deflated Sharpe 0,949 bei 13 Versuchen. Permutationstest p 0,009, das besteht die
     Bonferroni-Korrektur für 13 Versuche knapp nicht.
   - Mechanismus: Nach Rückgängen steigen Volatilität und Dealer-Short-Gamma, Intraday-Moves
     laufen weiter. In ruhigen Aufwärtstrends ist die Opening Range nur Rauschen.
   - Passt zum Residual-Check (ORB schwach im Bullenmarkt 2023–26) und zum IBD-Befund.
   - Risiko: Das IS 2019–22 enthält den Covid-Crash und den Bärenmarkt 2022, Rückgänge sind
     also überrepräsentiert.
2. **CTNL: kein Einstieg an US-High-Impact-Tagen** (NFP, CPI, Retail Sales, GDP; FRED).
   - IS: Ø R 1,20 statt 0,84, PF 2,85, DD 11,7 statt 19,1 %, 85 von 109 Trades.
   - Permutationstest p 0,003, das besteht Bonferroni für 14 Versuche.
   - Mechanismus: Datenspitzen laufen über den 3-ATR-Stop, bevor die Umkehr greift.
   - Risiko: Es wurden nur 24 Trades entfernt.

## Echte Fills (EK, 01.09.–23.10.)
- ORB 35 Positionen, CTNL 29.
- Abgleich mit der Tickmill-Simulation in UTC (±60 Min.):
  - ORB: 12 von 34 echten Trades finden sich in der Simulation.
  - **CTNL: 1 von 27.** Bis 30.09. ist das großteils die bekannte Orderflut
    (Memory „CTNL: Sim-Filter ist kein Live-Gate“). **Ab 01.10. sind es aber immer
    noch 6 von 7 echten Trades ohne Gegenstück in der Simulation.** Ungeklärt, siehe
    DASHBOARD „Offene Aufgaben“.
- Die Coach-Annahme „Deckel 2“ war meine. Die EK-Bridge zählt ihre echten Positionen
  selbst. Dass 3 gleichzeitig offen waren, ist deshalb nicht sicher ein Verstoß.

## Praktische Lehren zu den Skills
- **FMP Free-Tier:** Wirtschaftskalender und COT liefern Fehler 402. Kurse für US-Aktien
  gehen.
- Die meisten Kontext-Skills rechnen nur den Stand von heute. Historisch nutzbar sind sie
  nur, wenn man ihre Rechenfunktionen je Stichtag aufruft (`filters.py`). Ein
  eingebautes `as_of` haben nur IBD, Markttop, COT und Exposure.
- Die Skripte schreiben nach `reports/` im aktuellen Arbeitsordner, darum nie in
  `knowledge/` starten.
- Die MT5-Brücke `scripts/mt5_tester_lock.py` lässt `mt5-robot-tester` nur innerhalb von
  IS laufen. Sie blockiert alle 9 Bridge-Terminals und zählt die Durchgänge per
  `log_trials`.
