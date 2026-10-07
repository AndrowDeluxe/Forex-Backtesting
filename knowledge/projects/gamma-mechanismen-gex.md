# Gamma-Mechanismen aus echten GEX-Daten (SqueezeMetrics)

**Status: abgeschlossen (07.10.2026, Nutzerentscheid).** Weiter läuft nur der Forward-Test bis 31.12.2026.

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

## Gamma als Regler im ORB, 01/2025–09/2026 (07.10., beschreibend)

Skript `scripts/research_orb_gamma_regler_2025.py`. Der Zeitraum ist bereits
gesehen; die Regler sind vorab festgelegt, aber nicht blind geprüft. Konto:
100k ab 01.01.2025, 1 % vom Kontostand × Regler-Gewicht.

| Version | Regler | Trades | Σ R | PF | Konto | MaxDD |
|---|---|---|---|---|---|---|
| SP500 live | ohne | 91 | +20,2 | 1,25 | 118,4k | −20,1 % |
| SP500 live | nur Q2–Q4 | 53 | +12,0 | 1,25 | 110,6k | **−10,6 %** |
| SP500 Basis (1. Ausbruch, beide Richtungen) | ohne | 449 | +5,2 | 1,01 | 88,4k | −42,7 % |
| SP500 Basis | **nur Q2–Q4** | 247 | **+47,1** | **1,23** | **141,6k** | −27,9 % |
| NASDAQ live | ohne | 147 | **+73,1** | **1,55** | **181,3k** | −19,3 % |
| NASDAQ live | kein Q5 | 109 | +34,9 | 1,35 | 128,8k | −16,6 % |
| NASDAQ live | Q1+Q5 halbes Risiko | 147 | +55,2 | 1,55 | 157,9k | −16,6 % |
| NASDAQ Basis | ohne | 449 | −10,0 | 0,97 | 78,4k | −51,7 % |
| NASDAQ Basis | nur Q2–Q4 | 247 | +4,6 | 1,02 | 96,1k | −25,1 % |

**Befund:**
- **An den Gamma-Extremen nicht zu handeln senkt den Drawdown in jeder
  Version** (z. B. SP500 live −20 % → −11 %). Bei den Grundversionen hebt es
  auch den Ertrag (SP500 Basis +5 R → +47 R).
- **Bei der NASDAQ-Live-Version kostet jeder Gamma-Regler Ertrag:** Deren
  Q5-Tage waren 2025–26 profitabel (Σ R +73 → +35 ohne Q5). Diese Version
  ist allerdings vorbelastet.
- **Aktuell (Q3 2026):** SP500 live −8,5 R, durch keinen Regler zu retten.
  NASDAQ live +32,8 R.
- **Kein universeller Gewinn:** Gamma ist ein guter Drawdown-Dämpfer, aber
  kein verlässlicher Ertragshebel für jede Version.

## Ergebnis blinder Test 06/2012–07/2016 (07.10., einmal geöffnet)

| | SP500 | NASDAQ |
|---|---|---|
| R1 Median-Range Q1 / Q5 | 1,17 % / 0,58 % = **2,0×**, Spearman −1,0 | 1,39 % / 0,73 % = **1,9×**, Spearman −1,0 |
| R2 Ø R Q5 gegen Q1–Q4 | 4,97 / 9,47 (ungültig, siehe unten) | **0,76 / 0,24** → Q5 besser |

**Urteil (vorab registriert):**
- **R1 Volatilität: BESTANDEN** bei beiden Indizes, perfekt monoton.
  Gamma → Tagesrange ist damit blind bestätigt (2012–16, 2016–22, 2023–24,
  2025–26).
- **R2 Kein Ausbruch bei viel Gamma: NICHT bestanden.**

**Datenqualität:** Die Dukascopy-Indexdaten 2012–13 sind lückenhaft:
- ~37 % der M15-Bars ohne Volumen
- ATR SP500 2012 bei 0,1 bps, 2013 bei 3,6 bps (normal 10–15 bps)
- ORB-Range 2012 praktisch null

Ein ATR-basierter Stop wird dadurch winzig, und die R-Werte blähen sich auf
(SP500 bis +18 R je Trade). Für R2 ist der Test deshalb nicht aussagekräftig.
Bei NASDAQ (plausiblere Werte) spricht er aber gegen die Regel. **Kein
nachträglicher Neutest:** Das wäre Nachjustieren nach dem Öffnen.
R1 nutzt nur die Rangfolge der Tagesrange zwischen den Quintilen und ist
gegen den Fehler robuster.

**Folge:** Gamma bleibt als **Volatilitäts- und Risikoregler** belegt. Den
Ausbruchsfilter „kein ORB bei viel Gamma“ verwerfen wir als Edge-Regel.
