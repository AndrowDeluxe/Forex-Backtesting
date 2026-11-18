---
title: NASDAQ-ORB aus der Vorbörsen-Range 09:00–09:30 NY
datum: 2026-11-15
status: Research, Tresor zu, nicht live
lock: nasdaq_orb_premarket_20261115
---

# NASDAQ-ORB aus der Vorbörsen-Range 09:00–09:30 NY

Nutzerauftrag 15.11.2026 (Anlass: ORB-News). Skript `scripts/research_nasdaq_orb_premarket.py`,
Ergebnisse `ny_open_orb/results/premarket_0900/` (`grid.csv`, `vergleich.csv`, `jahre.csv`, `filter.csv`,
`filter_zustaende.csv`, `m1_check.csv`).

## Aufbau

- Range = Hoch/Tief 09:00–09:30 NY (M5). Ab 09:30 Stop-Orders an beiden Enden (OCO), Einstieg bis 12:00.
  SL am anderen Range-Ende, Ausstieg SL / TP / Tagesschluss 16:00.
- Kosten wie alle ORB-Läufe: 0,54 bps Spread + 0,45 + 0,30 bps Slippage.
- Split: IS 07/2016–2022, OOS 2023–14.05.2026, Tresor 15.05.–14.11.2026 (zu).
- Gitter (nur IS ausgewählt): 9 Ranges × 3 SL × 6 TP × 4 Trendfilter = 648 Varianten.
- Gegenprobe auf M1 (genauere Reihenfolge in der 09:30-Kerze) und mit höheren Kosten.

## Ergebnis (M1, Ø R netto je Trade)

| Variante | IS Ø R | IS t | OOS Ø R | OOS t | Trades/Jahr |
|---|---:|---:|---:|---:|---:|
| Nutzer-Spec 09:00–09:30, EMA50/200 M5, Tagesschluss | 0,09 | 1,2 | 0,06 | 0,6 | ~210 |
| dieselbe ohne Trendfilter | **0,17** | 2,2 | **0,28** | 2,7 | ~248 |
| IS-Gewinner 08:00–09:30, ohne Trend, Tagesschluss | 0,14 | 2,7 | 0,10 | 1,6 | ~246 |
| unser NASDAQ-ORB live (09:30–09:45, 0,6 ATR) | 0,23 | 1,3 | 0,19 | 0,8 | ~70–78 |

- **Der EMA-Trendfilter schadet** auf jeder Zeitebene (M5, H1, D1). Auf M5-Daten sah er sogar tief negativ
  aus (−0,18 R). Das war ein Artefakt: Mit nur einer erlaubten Seite füllt die Order oft erst nach einem
  Fehlausbruch zur Gegenseite, und in einer M5-Kerze, die beide Enden berührt, zählt der Stop. Auf M1 bleibt
  ein schwaches Plus, aber unter der ungefilterten Version.
- **Feste TPs schaden**: 1R und 2R sind deutlich negativ, 4R schwächer als Tagesschluss. Der Ertrag kommt
  aus den wenigen Tagen, die bis Schluss durchlaufen (Trefferquote ~21 %).
- **SL näher als das Range-Ende** (0,75 / 0,5 Breite) ist durchgehend schlechter.
- 75–90 % der Einstiege fallen in die erste Minute nach 09:30. Es ist im Kern Eröffnungsmomentum gegen die
  Vorbörsen-Range.
- Deflated Sharpe des IS-Gewinners ≈ 0 bei 648 Varianten. Die ungefilterte Nutzer-Version war vorab
  spezifiziert, ist aber durch das Weglassen des Filters ebenfalls ein Schritt nach Sicht.

## Kosten sind der Knackpunkt

Der Median-Stop ist nur ~24 NASDAQ-Punkte. Darum:

- Kosten ×2: IS 0,08 (t 1,1), OOS 0,21 (t 2,0)
- +5 Punkte Eröffnungs-Slippage je Trade: IS −0,28, OOS +0,13

Echte Stop-Fills um 09:30:00 auf dem CFD sind genau dort, wo Spreads am breitesten sind. Ohne gemessene
Live-Fills zur Eröffnung ist der Edge nicht belastbar. Unsere Bridges pollen zudem; der Einstieg muss als
Broker-Stop-Order vor 09:30 liegen (siehe [[orb-first-bar-and-polled-exits]]).

## Richtungsfilter (Regel auf IS gelernt, dann OOS)

Basis: Nutzer-Version ohne EMA. Je Zustand bleiben die Seiten mit IS-Ø R > 0.

| Filter | IS-Regel | OOS Ø R behalten / entfernt | Urteil |
|---|---|---|---|
| VIX ≥ 20 | nichts entfernt | — | kein Hebel (OOS short bei VIX ≥ 20 −0,26, im IS nicht sichtbar) |
| VIX gegen 20-Tage-Schnitt | short bei fallendem VIX weg | 0,33 / 0,14 | Ø besser, Σ R kleiner (206 vs. 237), schwach |
| Realzins-Trend 20 T. | short bei fallendem Realzins weg | 0,29 / 0,28 | kein Effekt |
| Stress (TAIL / STLFSI > 1) | Stress-Tage weg | 0,27 / **0,79** | schadet (entfernt Gewinner, n 20) |
| Regime (Landi, Wachstum × Inflation) | g↓π↑ weg | OOS kein solcher Tag | nicht prüfbar, OOS nur ein Regime |
| EMA50/200 (M5/H1/D1) | — | schlechter als ohne | schadet |

Bestätigt [[makro-filter-hilft-edges-nicht]]: Makro/Stress/Regime taugen als Kontext, nicht als Schalter.

## Vergleich und Kombination mit dem Live-ORB

Tages-Korrelation zum Live-NASDAQ-ORB 0,29 (668 gemeinsame Tage). OOS-Tages-Sharpe (annualisiert): neu 1,5,
live 0,4, risikogleich kombiniert 1,2. Die neue Variante ist im Backtest stärker, aber kostenempfindlicher.

## Vier-Fragen-Check

1. Geld verdient: Bricht der Kurs zur Cash-Eröffnung aus der Vorbörsen-Range, läuft er an einigen Tagen bis
   Schluss weiter (Eröffnungsmomentum).
2. Größter Verlust (IS): 2017 und 2020, Short-Seite schwächer (IS short 0,08 vs. long 0,24).
3. Was dort anders ist: viele kleine Ranges mit Fehlausbrüchen, 2020 extreme Eröffnungs-Gaps.
4. Eine Regel: Mindest-Range-Breite in bps (gegen Kostenquote); noch nicht getestet, wäre gezählte Variante.

## Nächster Schritt (offen, nicht beschlossen)

Vor jedem Tresor: Eröffnungs-Fills messen (echte Spreads/Slippage 09:30 auf TTP/IQ/Tickmill), dann ggf.
Kandidat einfrieren (ungefiltert, SL Range-Ende, Tagesschluss) und Tresor einmal öffnen.

## Runde 2 (15.11.): Puffer-Stop-Order + Trendfilter-Kombinationen, M1

Skript `scripts/research_nasdaq_orb_premarket_v2.py`, Ergebnisse `v2_rangliste.csv` (nach IS-Sharpe sortiert, OOS
daneben), `v2_kostenstress_top15.csv`. Range 09:00–09:30 fest, Stop-Order vor 09:30 beim Broker, Puffer 0/0,05/0,1/0,2
Range-Breiten, 20 Trendfilter (EMA-Paare M5–D1, Kombis, Gap, Vortag, Kurs vs. EMA200) je einseitig oder mit Storno
bei Gegenausbruch, TP 2/3/4/6 R/Tagesschluss. 680 Varianten (Lock jetzt 1.338 Versuche).

| Variante | IS Ø R | IS Sharpe ann. | IS MaxDD % (0,5 %) | OOS Ø R | OOS Sharpe ann. | OOS MaxDD R |
|---|---:|---:|---:|---:|---:|---:|
| #1 IS: EMA50/200 M15, Storno, Puffer 0,2, Tagesschluss | 0,29 | 1,15 | −18 % | 0,24 | 1,07 | −51 |
| #3 IS: Kurs vs. EMA200 D1, Storno, Puffer 0 | 0,29 | 1,11 | −15 % | 0,18 | 0,78 | −24 |
| ohne Filter, Puffer 0 (Rang 43) | 0,17 | 0,89 | −31 % | 0,28 | 1,50 | −39 |

- **Storno ist der Schlüssel:** Trendfilter einseitig Median IS-Sharpe 0,49; mit Storno 0,82. Mit Storno heben die
  Filter Ø R je Trade (+0,29 statt +0,17) bei halber Trade-Zahl (~119/Jahr) und halbem IS-Drawdown.
- **Im OOS schlägt kein Filter die ungefilterte Version** (Sharpe 1,50). Rangfolge IS→OOS hält nur mäßig (Spearman 0,53).
- **Puffer bringt nichts** (Median-Sharpe 0 → 0,2: 0,68 → 0,71 IS, 0,65 → 0,64 OOS). Er spart keine Kosten, der
  Kostenvorteil kommt allein vom vorab gelegten Stop statt Market-Order.
- **TP:** 2R negativ, Tagesschluss/6R am besten.
- **Kosten ×3:** #1 bleibt IS +0,15 / OOS +0,11 R; ungefiltert fällt IS auf ≈ 0. Der Filter macht die Variante
  kostenrobuster, nicht ertragreicher.

## Tresor (geöffnet 15.11.2026, echte Broker-Ticks)

Eingefroren vor dem Öffnen (Hash `53908ff0…`, `tresor_freeze.json`, 1.448 gezählte Versuche): A = EMA50/200 M15 +
Storno + Puffer 0,2 (Haupt), B ungefiltert, C Kurs vs. EMA200 D1 + Storno, D EMA9/21 H1 + Storno, E EMA20/50 H1 +
Storno, F Nutzer-Original (EMA50/200 M5 einseitig); alle Tagesschluss. Vergleich: Live-NASDAQ-ORB.
Skripte: `pull_broker_ticks_nasdaq.py`, `pull_broker_nasdaq_deals.py`, `research_nasdaq_orb_premarket_tresor.py`.
Ergebnis: `tresor_report.csv`, `tresor_trades_ticks.csv`, `tresor_kosten_gemessen.json`.

**Fill-Messung (Ticks 15.05.–13.11., TTP/Tickmill/IQ):** Spread 09:30 Median 1,0 Pkt. Stop-Einstieg 09:30 Median
1,1 Pkt, Ausstieg 0,6 Pkt, zusammen 1,04 bps (Modell 1,29 bps war konservativ). Echte Live-ORB-Deals bestätigen:
Einstieg 0,7–1,2 Pkt, Ausstieg 0,3–0,7 Pkt, Kommission 0. Die befürchteten +5 Pkt Eröffnungs-Slippage gibt es nicht.

**Tresor, Tick-Simulation mit echten Kosten (TTP / Tickmill):**

| Variante | n | Ø R | PF | Σ R | MaxDD R | Sharpe ann. |
|---|---:|---:|---:|---:|---:|---:|
| A Haupt | 75 / 74 | 0,23 / 0,25 | 1,31 / 1,33 | 17,5 / 18,6 | −16,6 / −15,6 | 1,01 / 1,07 |
| B ungefiltert | 126 | 0,37 / 0,37 | 1,47 | 46,7 / 46,6 | −18,1 / −18,0 | 1,90 / 1,91 |
| C Kurs vs. EMA200 D1 | 60 | 0,66 / 0,66 | 1,85 | 39,3 / 39,6 | −11,2 / −11,0 | 2,00 / 2,03 |
| F Nutzer-Original | 105 | 0,00 / 0,02 | 1,00 | −0,5 / 1,8 | −29,6 / −28,1 | −0,02 / 0,08 |
| **Live-ORB** | 35 | **1,62 / 1,64** | 2,9 | **56,7 / 57,3** | −9,5 / −9,3 | **2,06 / 2,08** |

IQ (ab ~Juni) gleiche Rangfolge. Dukascopy-M1: A nur +0,09 R, B +0,26, C +0,57, Live +1,30.

- Erfolgskriterium A (Ø R > 0 auf TTP + Tickmill) formal erfüllt, aber schwach (t 0,7, Dukascopy +0,09).
- **Der Live-ORB schlägt im Tresor jede neue Variante** (Σ R, Sharpe, Drawdown).
- Kombination Live + B: Korrelation 0,47, Sharpe 2,31 statt 2,08 allein.
- Ergebnis hängt an zwei Monaten (Sept., Nov.); 6 Monate, t-Werte ~1,3–1,8, kein Beleg im strengen Sinn.
- Tick-Sim des Live-ORB storniert sofort bei SL-Berührung; live wird gepollt (Dukascopy-M1 47 statt 35 Trades,
  Differenz ~+4 R).
