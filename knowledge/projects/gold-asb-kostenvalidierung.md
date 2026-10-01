# Projekt: Gold ASB — Kosten-, Ausführungs- und Optimierungsprüfung

Status: **Proben + Optimierung abgeschlossen, Entscheidung offen** (2026-10-01).
Dritter Durchlauf von [[realkosten-und-ausfuehrungs-probe]] nach
[[cls-practical-kostenvalidierung]] und [[ctnl-kostenvalidierung]], plus
Nutzerauftrag: Einstieg, Order-Logik, Filter, BE und Ziele prüfen.
**Kein Bot wurde geändert.**

Skripte: `scripts/research_gold_asb_execution_costs.py` (Proben p6_5–p6_8),
`scripts/research_gold_asb_optimization.py` (M5-Engine, Varianten). Kosten-
messung: `_data/broker_spreads_xauusd_asb_entry.json` / `_exit.json`.

---

## Kurzfassung

1. **Das Bein ist kostenrobust.** Bei TTP-Kosten (teuerster Broker) Ø R
   +0,44 statt +0,51, bei doppelten TTP-Kosten noch +0,36. Der Stop ist im
   Median das **15-fache** der Round-Trip-Kosten. Gegenteil des CLS-Falls.
2. **Der Live-Versatz kostet nichts.** Market-Entry 15–60 Min. nach der
   Beruehrung: nicht monoton, Rauschen. Eine broker-seitige Stop-Order wäre
   operativ sauberer, bringt aber keinen messbaren Edge.
3. **EK verliert durch die Neuverankerung des Stops** ~0,04–0,07 R je Trade
   und hat den höheren Drawdown (−8,6 R statt −5,9 R). Gleiche Richtung wie
   bei CLS.
4. **BE, TP, Trailing und Teilausstieg verschlechtern ausnahmslos.** Jetzt
   auch auf dem gefilterten Satz und mit echten Kosten bestätigt (vorher nur
   ungefiltert getestet).
5. **Zwei Kandidaten bestehen den Walk-Forward:** Stop 1,5x Range statt 1,0x
   und Order-Storno 03:30–04:00 NY statt 02:00. Die Exit-Zeit besteht ihn nicht.
6. **Der Edge hat sich etwa halbiert:** IS 2016–21 Ø R +0,55, OOS 2022–26
   +0,25 (Sharpe 1,14 → 0,88). Er bleibt aber in **11 von 11 Jahren**
   positiv. Und er ist **keine Long-Trendwette**: Shorts tragen mehr
   (+0,54 R) als Longs (+0,36 R).

---

## Ausgangslage: Backtest und Live sind verschiedene Order-Typen

| | Backtest (`asian_range_breakout.engine`) | Funded / FK | EK |
|---|---|---|---|
| Order | ruhende OCO-Stop-Order | Market beim nächsten Scan | Market beim nächsten Scan |
| Fill | exakt am Range-Level | Live-Kurs | Live-Kurs |
| SL | Level − 1x Range | absolutes Signal-Niveau | **am Live-Kurs neu verankert** |
| Alters-Gate | — | 60 Min. | **6 h** |
| Hebel-Gate | — | 0,50R-Detektor | keins (bei Neuverankerung gegenstandslos) |

Echte Fills (4 Signale, `bridge_state_*.json`): Label der Fill-Bar 05:15 UTC,
Fill **05:43** → 28 Min. nach dem Label, also ~13 Min. nach Bar-Schluss.
Wie bei CTNL getaktet, nicht zufällig.

Konfiguration live (aus `challenge_portfolio/paper_bot.py::_scan_gold_asb`):
Range 21:00–01:00 NY, Stop 1,0x Range, kein TP/BE, Zeit-Exit 11:00 NY.
Filter: ADX≥15, SMA200-Trend, Delay≤3 M15-Bars, Silber-5T-Richtung,
kausaler Liquiditätsfilter. **189 Trades in 10 Jahren aus 2.746
ungefilterten**, die Filter behalten also 7 %.

---

## Probe 1 (p6_5) — Kosten

Gemessen im ASB-Fenster (07:00–08:15 und 16:45–17:30 Berlin, 30 Tage). Der
Spread ist über den Tag konstant, das Fenster spielt also keine Rolle.

| Broker | Spread | Slippage RT | Kommission | RT (Points) | bps |
|---|---|---|---|---|---|
| Tickmill (EK) | 8 | 8 | 0 | 16 | **0,38** |
| BeyondIQ (FK) | 26 | 2 | 5 | 33 | 0,79 |
| BeyondIQ (IQ) | 26 | 5 | 5 | 36 | 0,86 |
| TTP | 48 | 33,5 | 6 | 87,5 | **2,08** |

Die Engine rechnet fix 0,30 USD Spread + 0,10 USD Slippage. Das sind heute
~0,95 bps, 2016 waren es ~3,3 bps. Im Mittel liegt das in der richtigen
Größenordnung, auf TTP heute aber halb so hoch wie real.

| Kosten | Ø R | PF | ΣR | MaxDD |
|---|---|---|---|---|
| 0 | +0,508 | 2,25 | +96,1 | −5,2 R |
| Tickmill 0,38 bps | +0,495 | 2,20 | +93,5 | −5,3 R |
| TTP 2,08 bps | +0,435 | 1,98 | +82,3 | −5,8 R |
| 2x TTP | +0,362 | 1,75 | +68,5 | −6,4 R |

## Proben 2/3 (p6_6, p6_7) — Lag und Sizing-Nenner (TTP-Kosten)

| Lag nach Fill-Bar-Label | Funded (abs. SL, 0,50R) Ø R | Funded Hebel max | EK (neu verankert) Ø R / MaxDD |
|---|---|---|---|
| Backtest (Level) | +0,435 | 1,00 | +0,435 / −5,8 |
| 15 Min. | +0,464 | 1,73 | +0,392 / −5,9 |
| **30 Min. (real)** | **+0,454** | 1,87 | **+0,398 / −8,6** |
| 45 Min. | +0,486 | 1,92 | +0,421 / −7,4 |
| 60 Min. | +0,352 | 1,96 | +0,395 / −6,5 |

- Funded: die Kurve ist nicht monoton, der Lag ist also Rauschen. Ohne Gate
  liegt der Hebel bei maximal 3,5x. Das Gate verwirft bei Lag 30 fünf Trades
  mit Ø R ≈ 0 und kostet damit nichts.
- EK: bei jedem Lag schlechter als Funded, mit höherem Drawdown. Der
  CLS-Befund („das strukturelle Niveau trägt den Edge“) gilt hier
  abgeschwächt auch.

## Probe 4 (p6_8) — Stop gegen Kosten

Stop / RT-Kosten (TTP): Minimum 3,5x, 5 %-Quantil 6,9x, Median 15,4x. **Kein
Trade unter 3x.** Die engsten Stops (3–10x) sind sogar die besten Trades
(Ø R +0,74). Ein Kostenboden ist nicht nötig.

---

## Teil 2 — Einstieg, Order-Logik, Filter

Basis für alle Vergleiche: M5-Engine mit echter OCO-Stop-Order ab 01:00 NY,
Storno 02:00, TTP-Kosten. 204 Trades, Ø R +0,401, Sharpe 1,02,
MaxDD −6,6 R. `P(>0)` = Bootstrap-Wahrscheinlichkeit, dass die
Differenz der R-Summe positiv ist.

**Order-Logik — nichts schlägt die Stop-Order belastbar.**

| Variante | Ø R | ΣR | P(>0) |
|---|---|---|---|
| Stop-Order (Basis) | +0,401 | +81,9 | — |
| Einstieg erst nach M5-Schluss jenseits | +0,372 | +61,7 | 0,04 |
| Market +5 / +15 / +30 / +45 Min. | +0,42 / +0,39 / +0,45 / +0,52 | | 0,33–0,83 |
| Retest-Limit am Level | +0,481 | +86,5 | 0,70 |

Der verzögerte Market-Einstieg sieht teils besser aus, liegt aber im
Rauschen (wie bei CTNL). Das ist **kein** Argument für absichtliches Warten.
Die Close-Bestätigung kostet signifikant.

**Einstiegsfenster (Storno-Zeit) — Kandidat.**

| Storno | n | Ø R | ΣR | MaxDD | R/DD | Sharpe |
|---|---|---|---|---|---|---|
| **02:00 (heute)** | 204 | +0,401 | +81,9 | −6,6 | 12,3 | 1,02 |
| 03:00 | 281 | +0,368 | +103,3 | −5,9 | 17,4 | 1,16 |
| 03:30 | 304 | +0,369 | +112,1 | −7,0 | 16,1 | 1,17 |
| 04:00 | 317 | +0,349 | +110,7 | −8,0 | 13,8 | 1,15 |
| 11:00 | 351 | +0,283 | +99,4 | −8,6 | — | — |

Walk-Forward (expandierend, Testjahre 2019–26): wählt 03:30–04:00 in 7 von 8
Jahren, OOS-Sharpe 1,03 statt 0,91. **Der Haken:** die Zusatztrades (Einstieg
02:00–03:00) tragen sich nur über die Shorts (n=29, Ø +0,67 R). Die Longs
liegen bei ±0, von 03:00–04:00 sogar negativ. Damit ist der Kandidat
plausibel, aber schmal belegt.

Kleine Randnotiz: die Engine beginnt die Fill-Suche erst bei 01:15 (sie
überspringt die erste Bar nach Range-Schluss) und füllt dann zum Level. Das
ist unschädlich: die echte OCO ab 01:00 liefert praktisch dasselbe
(ΣR −3,2, P 0,26). Die 01:00-Bar-Fills sind sogar die besten (Ø R +0,52).

**Filter — die heutige Kette ist gut begründet, nichts zu ändern.**

| Variante | n | Ø R | ΣR | MaxDD | Bewertung |
|---|---|---|---|---|---|
| ohne Silber | 328 | +0,194 | +63,7 | −15,3 | stärkster Filter |
| ohne Liquidität | 333 | +0,266 | +88,5 | −11,1 | klare Qualitätswirkung |
| ohne Trend | 367 | +0,315 | +115,6 | −10,8 | verworfene Trades Ø +0,21, aber klumpig (2017/21/22 tragen alles) |
| ohne ADX | 241 | +0,372 | +89,8 | −8,5 | ADX 10–17,5 ist ein Plateau, 15 passt |

---

## Teil 3 — Ausstieg und Ziele

Alles auf dem gefilterten Satz, TTP-Kosten. ΔΣR gegen die Basis (+81,9):

| Mechanismus | bestes getestetes Level | ΔΣR | P(>0) |
|---|---|---|---|
| Break-even (0,5–3R) | 3R | −11,4 | 0,14 |
| Take-Profit (1–6R) | 4R | −6,2 | 0,28 |
| Trailing (6 Varianten) | ab 3R, Abstand 2R | +2,6 | 0,65 |
| 50 % Teilausstieg (1–3R) | 3R | −3,9 | 0,27 |

BE bei 0,5R halbiert das Ergebnis (+35,1). Der Mechanismus ist derselbe wie
beim ungefilterten Test vom August: Zeit-Exit-Gewinner werden bei einem
Rücksetzer abgewürgt. **Alles verwerfen.**

**Zeit-Exit:** später ist im Gesamtsample besser (16:45 NY: Ø R +0,505 statt
+0,401, vor allem durch Shorts). Aber der Walk-Forward springt zwischen 10:15
und 16:45 hin und her. **Nicht ändern.**

**Stop-Faktor — Kandidat.**

| Stop x Range | Ø R | ΣR | MaxDD | R/DD | Sharpe | Sharpe IS / OOS |
|---|---|---|---|---|---|---|
| 1,0 (heute) | +0,401 | +81,9 | −6,6 | 12,3 | 1,02 | 1,14 / 0,88 |
| 1,25 | +0,373 | +76,1 | −4,8 | 16,0 | 1,15 | 1,14 / 1,22 |
| **1,5** | +0,335 | +68,3 | −4,5 | 15,3 | **1,20** | 1,16 / 1,33 |
| 2,0 | +0,244 | +49,9 | −4,1 | 12,1 | 1,13 | 1,05 / 1,31 |
| 2,5 | +0,227 | +46,3 | −3,3 | 14,0 | 1,31 | 1,04 / 1,81 |

Der Walk-Forward wählt 1,5 in 7 von 8 Jahren (OOS-Sharpe 1,07 statt 0,91).
In R gemessen sinkt der Ertrag. Bei gleichem Drawdown könnte man das Risiko
aber um ~1,47x erhöhen und läge dann bei ≈ +100 R statt +82. **Warnsignal:**
die Werte über 2,0 sind zackig, und der Gewinn sitzt im OOS-Zeitraum. Das
deutet auf das volatilere Gold-Regime seit 2022, nicht auf einen
Strukturbefund. 1,25–1,5 ist das Plateau. Den Rand des Gitters würde ich
nicht nehmen.

**⚠️ EK-Mindestlot:** bei 1,0x braucht `gold_asb` ~2.057 EUR Equity für
kalibrierte Größe ([[ek-risiko-kalibrierung-audit]]). Bei 1,5x wären es
~3.090 EUR, also über EKs heutiger Equity (~2.900). **Auf EK würde ein
breiterer Stop das Risiko ERHÖHEN statt die Lots zu senken.** Für EK also
nicht ohne Weiteres übertragbar.

---

## Kombinationen (In-Sample gewählt, nur als Orientierung)

| Variante | n | Ø R | ΣR | MaxDD | R/DD | Sharpe | Sharpe IS / OOS |
|---|---|---|---|---|---|---|---|
| Basis | 204 | +0,401 | +81,9 | −6,6 | 12,3 | 1,02 | 1,14 / 0,88 |
| Storno 03:00 + Stop 1,5 | 281 | +0,285 | +80,1 | −5,1 | 15,7 | 1,26 | 1,19 / 1,42 |
| Storno 03:00 + Stop 1,5 + Exit 16:45 | 281 | +0,341 | +96,0 | −5,5 | 17,4 | 1,35 | 1,21 / 1,62 |

Diese Kombinationen sind auf denselben Daten ausgewählt. Die Sharpe-Werte
sind deshalb optimistisch. Belastbar sind nur die Einzel-Walk-Forwards oben.

---

## Entscheidungsvorlage

| # | Vorschlag | Belege | Risiko |
|---|---|---|---|
| A | Stop 1,0 → **1,25–1,5x Range** (Funded/FK) | WF stabil, Sharpe +0,18, DD −30 % | Gewinn OOS-lastig (Regime); auf EK Mindestlot |
| B | Storno 02:00 → **03:00** (= `GOLD_ASB_MAX_DELAY_BARS` 3 → 7) | WF stabil, Sharpe +0,14, ΣR +21 | Zusatztrades nur über Shorts (n=29) |
| C | EK: SL **absolut** statt neu verankert | +0,05 R/Trade, DD −8,6 → −5,9 R | Code-Änderung in einer Datei ohne Git-Netz |
| — | BE / TP / Trailing / Teilausstieg / Close-Bestätigung / Filterumbau | alle schlechter oder Rauschen | **verwerfen** |

Wichtig: `challenge_portfolio/paper_bot.py` wird von der Funded-Bridge
**direkt importiert**. Jede Änderung an A oder B wirkt dort sofort live.
