# Gamma-Mechanismen aus echten GEX-Daten (SqueezeMetrics)

Untersucht 2026-10-07 (Nutzerauftrag: „Leite aus den Gamma-Werten
Mechanismen/Regeln ab, vor allem nach dem Kippen, und wie wir sie für einen
nachhaltigen Edge nutzen“). Skript `scripts/research_gex_mechanisms.py`,
Ausgabe `ny_open_orb/results/gex_mechanisms.txt`.

**Status: Hypothesen-Suche auf schon gesehenen Daten,** kein Edge-Beleg.

**Gamma-Maß:** SPX-GEX vom Vortag als Perzentil der letzten 252 Tage, in
Quintile eingeteilt (Q1 = wenig, Q5 = viel positives Dealer-Gamma).

**Perioden:** 2016–2022 | 2023–2024 | 2025–09/2026.

**Gesucht:** Zusammenhänge, die einen Mechanismus haben **und** in allen
Perioden dasselbe Vorzeichen zeigen.

## Ergebnisse

### M1 Volatilität: robust, monoton, in allen Perioden ✅

Mediane Tagesrange SP500 (%):

| | 2016–22 | 2023–24 | 2025–26 |
|---|---|---|---|
| Q1 wenig Gamma | 1,73 | 1,25 | 1,40 |
| Q5 viel Gamma | 0,56 | 0,70 | 0,64 |

NASDAQ zeigt dasselbe Bild (2,25 → 0,77 usw.). Viel Dealer-Gamma heißt eine
2–3-mal ruhigere Sitzung. **Mechanismus:** Long-Gamma-Dealer hedgen gegen
die Bewegung.

### M2 Trend oder Umkehr intraday: instabil ❌

Die Korrelation zwischen den ersten 30 Minuten und dem Rest des Tages
wechselt je Quintil und Periode das Vorzeichen. Daraus folgt keine Regel.

### M3 ORB (1. Ausbruch) bei viel Gamma (Q5): negativ in 5 von 6 Index-Perioden ✅ (schwach)

| Ø R | 2016–22 | 2023–24 | 2025–26 |
|---|---|---|---|
| SP500 | −0,28 | −0,14 | −0,06 |
| NASDAQ | −0,12 | +0,02 | −0,05 |

Q5 sind ~20–40 % der Tage. Ohne Q5 wird SP500 im IS +0,15 statt +0,04;
später ist die Wirkung klein. **Mechanismus:** Ausbrüche laufen gegen
dämpfende Dealer, und die kleine Range macht die Kosten relativ teuer.

### M3 Fade nach Gamma: kein stabiles Muster ❌

Bei Q4 ist der Fade überall negativ, das spricht sogar gegen die
Umkehr-These.

### M3b Ribbon × Gamma

| Ø R | 2016–22 | 2023–24 | 2025–26 |
|---|---|---|---|
| „neutral“ bei viel Gamma, SP500 | +0,97 | −0,06 | +0,21 |
| „neutral“ bei viel Gamma, NASDAQ | +0,96 | +0,05 | **+0,85** |
| „neutral“ bei wenig Gamma, SP500 | +0,26 | +0,36 | **−0,27** |
| „neutral“ bei wenig Gamma, NASDAQ | +0,31 | +0,55 | **−0,08** |

Der Ribbon-Kipp 2026 sitzt also in den **Tagen mit wenig Gamma**. Die Zellen
nach 2023 haben aber nur Dutzende Trades, das ist instabil.

### M4 DIX → SPX-Rendite der nächsten 20 Tage: 3 von 4 Perioden ✅ (vorsichtig)

| Ø 20-Tage-Rendite | 2012–16 | 2016–22 | 2023–24 | 2025–26 |
|---|---|---|---|---|
| DIX hoch (Q5) | +1,52 % | +1,49 % | +0,71 % (Ausnahme) | +2,10 % |
| übrige Quintile | ~0,3–0,9 % | ~0,3–0,9 % | | |

Achtung: Die 20-Tage-Renditen überlappen, und es gibt Bullenmarkt-Drift.

## Nutzbar für einen nachhaltigen Edge (Kandidaten, noch vorab zu registrieren)

1. **Gamma als Risiko- und Volatilitätsregler (M1)** ist der robusteste
   Befund. Er ist kein eigener Edge, aber für jede Intraday-Strategie
   nutzbar: Stop/Ziel und Positionsgröße an der erwarteten Range ausrichten,
   an Tagen mit wenig Gamma kleiner handeln.
2. **„Kein Ausbruchs-Trade bei sehr viel Gamma (Q5)“ (M3):** Der
   Mechanismus ist klar, das Vorzeichen stabil, die Wirkung klein.
3. **DIX als langsamer Swing-Filter (M4):** Long-Bias bei hohem DIX.
   Anderer Zeithorizont, wenig Kosten; braucht einen eigenen, sauberen Test
   (nicht überlappende Positionen, Kosten, Drawdown).

**Sauberer Prüfweg:** Die Zeit vor 2016 (GEX ab 05/2011) wurde in keiner
unserer ORB-Studien benutzt. Gibt es dafür M1-Daten (Dukascopy), kann
2011–07/2016 als **echter, blinder Vergangenheits-Tresor** für vorab
registrierte Gamma-Regeln dienen. Dazu kommt der Forward-Test ab 10/2026.

Verwandt: [[baltussen-tagesend-momentum]], [[orb-neues-regime-2026]],
[[orb-order-storno-und-haltedauer]].

## Vorab-Registrierung blinder Test 06/2012–07/2016 (07.10., VOR dem Laden der Daten)

Skript `scripts/research_gamma_rules_blind.py`, Lock `gamma_rules_blind_20261007`.
Die M1-Daten beginnen bei Dukascopy im Mai 2012. Bisher hat keine Studie
Daten vor dem 28.07.2016 genutzt. Getestet wird einmal; das Ergebnis zählt.

| Regel | Bestanden, wenn … (für beide Indizes) |
|---|---|
| **R1 Volatilität** | Median-Tagesrange Q1 ≥ 1,5 × Q5 **und** Spearman(Quintil, Median) ≤ −0,9 |
| **R2 Kein Ausbruch bei viel Gamma** | ORB 1. Ausbruch (beide Richtungen, Stop 1,0 ATR, Exit 16:00): Ø R(Q5) < Ø R(Q1–Q4); **stark**, wenn zusätzlich Ø R(Q5) < 0 |

Nicht blind testbar und deshalb ausgelassen: die DIX-Regel (2012–2016 wurde
schon angesehen).
