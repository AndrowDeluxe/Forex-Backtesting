# ORB im neuen Regime (ab 10/2025): N-ter Ausbruch, Fade, IS = der Bruch

**Status: abgeschlossen (07.10.2026, Nutzerentscheid).** Weiter läuft nur der Forward-Test bis 31.12.2026.

Gestartet 2026-10-06 (Nutzerauftrag), unabhängig von der Mentor-PDF.
Vorgeschichte: [[orb-order-storno-und-haltedauer]] (IS-only-Test, Tresor
durchgefallen, Ribbon-Filter kippt) und [[overfitting-sperre]].

## Split (Lock `ny_open_orb_regime2026_20261006`)

| Stufe | Zeitraum | Status |
|---|---|---|
| IS | 01.10.2025–31.03.2026 | der Bruch, hier wird optimiert |
| OOS | 01.04.–30.06.2026 | einmal |
| Backtest-Tresor | 01.07.–30.09.2026 | **vorbelastet** (Diagnose kennt 2026) |
| Forward | ab 05.10.2026 | echter blinder Test, öffnen bei ≥ 100 Trades je Index oder am 31.03.2027 |

## Untersuchung „N-ter Ausbruch“ (beschreibend, keine Auswahl)

Skript `scripts/research_orb_nth_breakout_study.py`. Der Einstiegs-Finder ist
`ny_open_orb/entries_nth.py` (getestet; Modus `first` liefert identische
Trades zu `find_live_entries`, 2.486 / 2.488). Feste Exit-Config: Stop
1,0 × M15-ATR, Ausstieg 16:00, beide Richtungen, kein Filter. Ø R je Trade:

| Modus | SP500 alt 2016–09/2025 | SP500 neu (IS) | NASDAQ alt | NASDAQ neu (IS) |
|---|---|---|---|---|
| 1. Ausbruch | +0,01 | −0,12 | **+0,17** (t 2,8) | −0,16 |
| 2. Ausbruch derselben Seite | −0,04 | −0,08 | +0,07 | −0,23 |
| 3. Ausbruch derselben Seite | −0,06 | +0,44 (t 1,2) | −0,02 | −0,04 |
| Ausbruch nach Fehlausbruch der Gegenseite | −0,07 | +0,05 | +0,04 | **+1,13** (t 1,5, n 58) |
| Fade des 1. Ausbruchs | −0,08 | **+0,24** | −0,14 | **+0,49** (t 1,3) |
| Retest nach 1. Ausbruch | −0,18 | −0,22 | −0,05 | −0,45 |

Je Index und Periode gibt es im neuen Regime nur 58–127 Trades, kein t-Wert
liegt über 2. Ein Ziel von 1R ist in jeder Variante schlechter als der
Ausstieg 16:00, weil die Kosten (0,09–0,17 R je Trade) bei kleinem Ziel zu
schwer wiegen.

**Befund:**
1. **Der 2./3. Ausbruch ist kein besserer Einstieg.** Über 9 Jahre altes
   Regime war keiner besser als der erste. Im neuen Regime ist nur SP500 beim
   3. Ausbruch positiv; NASDAQ bestätigt das nicht. Das ist eher Rauschen.
2. **Im neuen Regime drehen die Umkehr-Einstiege ins Plus.** Fade und
   „Ausbruch nach Fehlausbruch“ (im Kern auch eine Umkehr) werden bei beiden
   Indizes positiv. Im alten Regime waren sie negativ. Der klassische
   Ausbruch und der Retest drehen ins Minus. Das passt zu Ladia (SSRN 2026,
   Opening-Range-Reversal seit 0DTE) und zur Gamma-Hypothese, ist aber
   statistisch noch dünn.
3. Die Retest-Einstiege sind in beiden Regimes die schlechtesten.

## IS-Optimierung (9 Punkte je Index)

Skript `scripts/research_orb_regime2026.py`. Suchraum und Auswahlregel stehen
im Docstring. Läuft seit 06.10. Ergebnis: siehe unten (Checkpoint vor OOS).

### Ergebnis IS-Stufe (06.10., Checkpoint, NICHT eingefroren)

46.656 Varianten je Index; 93.312 Trials stehen im Lock. Die
Mindestbedingungen erfüllen nur 117 (SP500) bzw. 98 (NASDAQ) Varianten.

| | SP500 | NASDAQ |
|---|---|---|
| Einstieg | **3. Ausbruch derselben Seite** | **Ausbruch nach Fehlausbruch der Gegenseite** |
| Richtung | long + short | long + short |
| Trendfilter | keiner | keiner |
| Eröffnungs-/VIX-Filter | keiner | keiner |
| Stop | 0,6 × ATR | 1,5 × ATR |
| Ziel | 4R | keins (Exit 16:00) |
| Spätester Einstieg | 12:30 | 16:00 |
| Range | 15 Min. | 15 Min. |
| IS: Trades / PF / Ø R / t | 114 / 1,68 / +0,51 / 2,3 | 58 / 2,26 / +0,77 / 1,5 |
| Deflated Sharpe | ~0 | ~0 |

- **SP500:** Die Top 50 sind alle Varianten des 3. Ausbruchs.
- **NASDAQ:** Die Top 50 sind fast nur Umkehr-Typen (Fade 21, Fehlausbruch 9,
  Short auf den 1. Ausbruch 16).
- **Statistisch schwach:** Die geglätteten t-Werte liegen nur bei 1,6 bzw.
  1,5. NASDAQ hat nur 58 Trades in 6 Monaten.

### OOS und Tresor (06.10., eingefroren, je einmal geöffnet): durchgefallen

| Neue Version | IS 10/25–03/26 | OOS 04–06/26 | Tresor 07–09/26 (vorbelastet) |
|---|---|---|---|
| SP500, 3. Ausbruch | +57 R, PF 1,66 | **−31 R, PF 0,43** | −8 R, PF 0,83 |
| NASDAQ, nach Fehlausbruch | +44 R, PF 2,20 | ±0 R, PF 1,00 | **−13 R, PF 0,41** |
| 100k-Konto, 1 % | | 72,4k (−27,6 %) | 80,1k (−19,9 %) |

Zum Vergleich die Live-Version auf denselben Zeiträumen, nur Backtest. Sie
wurde am 04.10. mit Blick auf 2026 gewählt und ist deshalb kein fairer
Vergleich:

| Live-Version | OOS | Tresor |
|---|---|---|
| SP500 | −4,9 R | −8,5 R |
| NASDAQ | +18,1 R | +32,8 R (PF 2,83) |

**Lehre:** Sechs Monate IS mit 46.656 Varianten sind fast reines Fitten.
Schon der IS-t-Wert lag nur bei 2,3 bzw. 1,5, die Deflated Sharpe bei ~0.
Auch das Umkehr-Muster aus dem Bruch-Halbjahr hielt nicht über Q2/Q3 2026.
Ein Regime-Wechsel lässt sich nicht aus dem halben Jahr lernen, in dem er
passiert. Bis genug neue Daten da sind, bleibt nur der Forward-Test.

**Für live relevant:** Die SP500-Live-Version liegt 2026 in beiden Fenstern
im Minus (Ribbon-Kipp). NASDAQ live ist positiv, aber vorbelastet.

## Einstiegsvarianten auf dem ursprünglichen IS 2016–2022 (07.10.)

Skript `scripts/research_orb_entries_is2016.py`, Lock
`ny_open_orb_entries_is2016_20261006`. Suchraum je Index: 6 Einstiegsarten
× 3 Richtungen × 4 Stops × 4 Ziele, ohne Filter. Die Auswahl lief auf IS
2016–2022, OOS wurde einmal geöffnet. Das OOS ist **nicht blind**, weil die
Untersuchung vom 06.10. diese Jahre schon beschreibend gesehen hat.

- **Nur 2 von 288 Varianten (NASDAQ) bestehen die IS-Bedingungen,** bei
  SP500 keine. Ohne Filter hat SP500 in keiner Einstiegsart einen Edge (PF
  im IS ≤ 1,15).
- **Der IS-Gewinner (NASDAQ) ist der klassische 1. Ausbruch,** nur long,
  Stop 0,6, Exit 16:00: IS +0,30 R (PF 1,34) → 2023–24 −0,01 → 2025–26
  +0,12.
- **Beste Variante je Einstiegsart, Ø R (IS / 2023–24 / 2025–09/26):**

  | Einstiegsart | NASDAQ | SP500 |
  |---|---|---|
  | 1. Ausbruch | +0,30 / −0,01 / +0,12 | |
  | nach Fehlausbruch | +0,19 / +0,04 / **+0,28** | |
  | 2. Ausbruch | +0,07 / +0,05 / −0,11 | |
  | 3. Ausbruch | +0,05 / +0,05 / −0,09 | |
  | Fade | −0,03 / +0,04 / −0,06 | −0,04 / +0,05 / −0,07 |
  | Retest | +0,01 / +0,02 / −0,19 | +0,03 / −0,04 / −0,15 |
  | übrige Einstiegsarten | | alle zwischen −0,10 und +0,10 |

**Befund:** Auf dem langen IS bleibt der 1. Ausbruch die beste
Einstiegsmethodik. Der 2./3. Ausbruch, der Fade und der Retest sind nicht
besser. Bei NASDAQ ist „nach Fehlausbruch“ die einzige Variante, die in allen
drei Perioden positiv ist (PF 1,21 / 1,04 / 1,31), aber mit kleinen Werten.
