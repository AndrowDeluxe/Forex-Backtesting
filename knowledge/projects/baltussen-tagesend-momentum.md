# Tagesend-Momentum nach Baltussen et al., mit echtem Dealer-Gamma

Getestet 2026-10-06 (Nutzerauftrag: „Teste den Baltussen-Edge als
Zwangsbedingung“). Skript `scripts/research_baltussen_late_momentum.py`,
Lock `baltussen_late_momentum_20261006`.

**Paper:** Baltussen, Da, Lammers, Martens (JFE 2021). Die Rendite vom
Vortagesschluss bis 30 Minuten vor Schluss sagt die letzte halbe Stunde
voraus. Ursache ist Gamma-Hedging von Dealern mit Short-Gamma und das
Rebalancing gehebelter ETFs, also ein Zwangs-Flow.

**Regel 1:1, ohne Optimierung:** Um 15:30 NY in Richtung der Rest-of-Day-
Rendite einsteigen, um 16:00 aussteigen. Kosten je Rundturn: SP500 1,59 bps,
NASDAQ 1,29 bps.

**Gamma-Daten:** SqueezeMetrics-GEX für SPX, täglich, 05/2011 bis heute,
kostenlos, eingefroren als `scripts/frozen_data/sqzme_dix_gex_20261006.csv`.
Verwendet wird der Wert vom Vortag.

## Ergebnis (netto bps je Trade; in Klammern t-Wert / Trades)

| Variante | SP500 IS 2016–22 | SP500 2023–24 | SP500 2025–09/26 | NASDAQ IS | NASDAQ 2023–24 | NASDAQ 2025–26 |
|---|---|---|---|---|---|---|
| A immer | −0,0 (−0,05) | −1,9 (−1,9) | −3,2 (−3,2 / 432) | +1,0 (1,0) | −2,4 (−2,1) | −3,2 (−2,4) |
| **B GEX < 0** (Dealer short Gamma) | **+7,4** (1,4 / 210) | −1,4 (−0,3 / 24) | **+7,5** (0,8 / 17) | **+7,7** (1,3) | +1,4 (0,2 / 24) | **+5,2** (0,4 / 17) |
| C GEX unteres Fünftel | +1,8 | −0,9 | −2,7 | +5,1 | −4,7 | −3,6 |
| D große Tagesbewegung | −0,0 | −1,3 | −2,9 | +2,7 | −4,3 | −4,4 |
| E C + D | +5,5 | +5,5 | +0,2 | +11,4 | −9,3 | −0,2 |
| Gegenprobe GEX oberes Fünftel | −0,3 | **−4,6 (t −4,0)** | −3,0 | −0,3 | −4,4 (−3,2) | −2,0 |

**Befund:**
1. **Ohne Bedingung ist der Effekt seit 2023 umgekehrt:** Das
   Momentum-Trading verliert signifikant, t ≈ −2 bis −2,4. Das passt zu
   FirmTape (Effekt in der 0DTE-Ära tot) und zu Adams et al. (0DTE dämpft
   Momentum).
2. **Bei negativem Gamma (B) zeigt das Vorzeichen in die vom Mechanismus
   vorhergesagte Richtung:** positiv im IS und im Zeitraum 2025–26, bei
   beiden Indizes. Aber es gibt nur 17–24 solche Tage je OOS-Fenster, kein
   t-Wert liegt über 2. Nicht handelbar, aber mechanisch stimmig.
3. **Bei viel positivem Gamma** (oberes Fünftel) **kehrt das Tagesende seit
   2023 um.** Das Momentum-Trading verliert dort −4,6 bps (SP500 2023–24,
   t −4,0). Im IS 2016–22 war es neutral. Long-Gamma-Dealer dämpfen
   inzwischen spürbar.

## Wichtige Korrektur zur ORB-Diagnose

Echtes GEX je Jahr (SPX, Vortag):

| Jahr | Anteil Tage mit GEX < 0 | Median-GEX (Mrd. $) |
|---|---|---|
| 2018 | 15 % | 2,5 |
| 2020 | 12 % | 3,4 |
| 2022 | **42 %** | 0,5 |
| 2025 | 4 % | 6,0 |
| 2026 | **4 %** | 5,5 |

**2026 war kein Jahr mit negativem Gamma.** Die Hypothese „der Ribbon-Filter
kippte, weil das Dealer-Gamma negativ wurde“ ([[orb-ribbon-filter-kippt-2026]])
wird von den echten Daten **nicht gestützt**. 2022 hatte viel mehr negatives
Gamma, und dort hielt der Filter. Die Ursache des Kipps bleibt offen.
Kandidaten sind das makrogetriebene Trendregime (Iran, Öl, Fed) oder etwas,
das das aggregierte SPX-GEX nicht abbildet, etwa das intraday wechselnde
0DTE-Gamma.

Verwandt: [[orb-neues-regime-2026]], [[orb-order-storno-und-haltedauer]].

## Erweiterung: Zeitfenster, Signale, SL/TP/Haltezeit (07.10.)

Skript `scripts/research_baltussen_extended.py`, Lock
`baltussen_extended_20261007`. 9.600 Varianten je Index (8 Punkte), Auswahl
nur auf IS 2016–2022. OOS ist nicht voll blind (Grundregel am 06.10. gesehen).

**Gewinner, für beide Indizes fast identisch:**
- Einstieg 15:45 in Richtung der **letzten Stunde** (14:45 → 15:45)
- nur an Tagen mit großer Bewegung (oberes Drittel), keine Gamma-Bedingung
- Stop 0,2 (SP500) bzw. 0,4 (NASDAQ) × Tages-ATR, Exit 16:00

Die Top 50 sind zu 100 % Momentum und zu 84 % 15:45. Haltezeit und Ziel
spielen bei 15:45 kaum eine Rolle (15 Minuten bis zum Schluss).

| Netto bps je Trade | IS 2016–22 | 2023–24 | 2025–09/26 |
|---|---|---|---|
| SP500 | **+5,3** (t 3,1, PF 1,64) | +1,3 (t 0,8) | **−1,8** (PF 0,79) |
| NASDAQ | **+6,6** (t 3,6, PF 1,73) | +2,9 (t 1,6) | **−0,2** (PF 0,98) |

Die Deflated Sharpe liegt bei ~0 (19.200 Varianten).

**Befund:** Momentum in den letzten 15 Minuten nach einer starken letzten
Stunde war 2016–2022 ein klarer Effekt. Seit 2023 schmilzt er, 2025–26 ist er
weg. Das ist dasselbe Muster wie beim ORB: Intraday-Momentum-Edges sterben in
der 0DTE-Ära. Das passt zu Adams et al. (0DTE dämpft Momentum) und zur
Gegenprobe oben (bei hohem Gamma kehrt das Tagesende um).
