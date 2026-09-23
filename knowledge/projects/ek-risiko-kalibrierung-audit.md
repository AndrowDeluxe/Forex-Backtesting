# Project: EK-Risikokalibrierung komplett nachgerechnet (Audit)

**Ziel**: Nutzerauftrag 2026-09-23 -- "Rechne die Kalibrierung einmal komplett
nach." Anlass war eine Differenz, die ich am 22.09. gefunden und damals als
ungeklaerten Widerspruch dargestellt hatte: dieselbe Rechnung ergab fuer EKs
Ist-Zustand P(MaxDD>40 %) = 33,9 %, waehrend der Kommentar in
`EK-Portfolio-Bridge/config.py` 7,8 % nennt.

**Status**: Abgeschlossen (2026-09-23). **Kein Fehler in der Kalibrierung.**
Nichts geaendert -- die Hebel-Entscheidung liegt beim Nutzer.
Skript: `scripts/research_ek_calibration_audit.py`.

## Ergebnis in einem Satz

Beide Zahlen sind richtig und messen verschiedene Zeithorizonte: **7,8 % ist
die Wahrscheinlichkeit, 40 % Drawdown innerhalb von rund zwei Jahren zu
reissen, 33-39 % die ueber die volle Sechsjahres-Historie.**

## Korrektur meiner Darstellung vom 2026-09-22

Ich hatte die Einheiten der Studie falsch gelesen (die combo-Prozente als
effektives Risiko je Trade statt als Werte VOR der Kapitalverduennung) und
daraus geschlossen, die Studienzahlen liessen sich nicht reproduzieren. Das
war falsch -- sie lassen sich vollstaendig reproduzieren. Meine damalige
Zusatzvermutung, es liege an der Bootstrap-Methode, war ebenfalls falsch und
hatte ich schon am selben Tag zurueckgenommen.

## Schritt 1: Die Rechenkette ist vollstaendig reproduzierbar

`portfolio_construction/results/ek_v2_realistic_final.json` speichert die
Kombination `riskopt_20dd`. Deren Prozente sind Risiko je Trade **innerhalb
der Kapitalscheibe von 1/6** (6 Kernbeine). Geteilt durch 6 und mit dem
dokumentierten Faktor 2,20 skaliert ergibt sich exakt der heute gefahrene
Stand:

| Bein | Studie | /6 = effektiv | heute live | Faktor |
|---|---|---|---|---|
| gold_asb | 8,00 % | 1,333 % | 2,934 % | 2,20x |
| trend_pullback | 5,00 % | 0,833 % | 1,834 % | 2,20x |
| btc_ema_cross | 8,00 % | 1,333 % | 2,934 % | 2,20x |
| gold_silver | 8,00 % | 1,333 % | 2,934 % | 2,20x |
| cls_practical | 1,50 % | 0,250 % | 0,550 % | 2,20x |
| **ou_modell** | 0,50 % | 0,083 % | **0,366 %** | **4,40x** |

Der Ist-Zustand reproduziert die im config-Kommentar dokumentierten Kennzahlen
punktgenau: **CAGR 227,8 %** (dokumentiert 227,8 %) und **MaxDD -38,1 %**
(dokumentiert -38,1 %).

## Schritt 2: Das Fenster erklaert die Differenz NICHT

Ist-Zustand auf dem Studienfenster (2018-12-01..2024-12-30) gegen heute:

| Fenster | CAGR | MaxDD | Sharpe | Tage |
|---|---|---|---|---|
| Studie (bis 2024-12-30) | 227,8 % | -38,1 % | 2,07 | 2.222 |
| bis heute (2026) | 219,3 % | -38,1 % | 2,06 | 2.816 |

## Schritt 3: Der Horizont erklaert sie vollstaendig

Die Studie nennt fuer den Ist-Zustand einen MC-Median-Drawdown von -26,1 % bei
einem historischen MaxDD von -38,1 %. Ein Median unter dem historischen Wert
ist nur moeglich, wenn kuerzere Pfade simuliert werden. Nachgerechnet:

| Simulierter Horizont | Methode | Median-DD | P(DD>40 %) |
|---|---|---|---|
| 1 Jahr | Monatsbloecke | -22,1 % | 3,6 % |
| 1 Jahr | iid-Tage | -21,3 % | 2,6 % |
| **2 Jahre** | Monatsbloecke | -29,8 % | 9,8 % |
| **2 Jahre** | **iid-Tage** | **-26,3 %** | **8,0 %** |
| 3 Jahre | Monatsbloecke | -33,3 % | 14,8 % |
| volle Historie | Monatsbloecke | -37,8 % | 39,3 % |

Die Zeile "2 Jahre / iid-Tage" trifft beide Studienzahlen (-26,1 % und 7,8 %).
Damit ist die Herkunft geklaert.

## Was das praktisch bedeutet

Bei unveraendertem Hebel gilt ueber mehrere Jahre:

- ein Rueckgang von **20 % oder mehr ist praktisch sicher** (P = 100 %)
- die **40 %-Grenze wird mit rund 39 % Wahrscheinlichkeit** irgendwann beruehrt

Hebel-Staffel (volle Historie, Block-Bootstrap ueber Monate):

| Hebel | CAGR | hist. MaxDD | P(DD>40 %) | P(DD>20 %) |
|---|---|---|---|---|
| 100 % (heute) | 227,8 % | -38,1 % | 39,3 % | 100 % |
| 85 % | 179,2 % | -33,0 % | 17,9 % | 99,8 % |
| **70 %** | **136,3 %** | -27,6 % | **4,6 %** | 98,0 % |
| 60 % | 110,8 % | -23,9 % | 1,1 % | 92,4 % |
| 50 % | 87,4 % | -20,1 % | 0,2 % | 54,9 % |

## Offene Entscheidungen fuer den Nutzer

1. **Welcher Horizont soll die Risikovorgabe steuern?** Wird EK ueber Jahre
   gefahren, ist die mehrjaehrige Zahl die relevante -- dann ist der heutige
   Hebel deutlich aggressiver als die dokumentierten 7,8 % suggerieren.
2. **`ou_modell` auf 2,20x zurueckziehen?** Es laeuft als einziges Bein mit
   doppeltem Gewicht gegenueber der dokumentierten Skalierung -- ausgerechnet
   das Bein, das laut [[ou-modell-kostenvalidierung]] out-of-sample negativ
   ist. Ob die 4,40x Absicht waren, ist nirgends dokumentiert.

## Verweise

- [[orb-exit-logik-neubewertung]] -- dort wurde die Differenz gefunden
- `scripts/research_ek_calibration_audit.py` -- Nachrechnung
- `scripts/research_ek_orb_risk_calibration.py` -- ORB-Kalibrierung (0,30 %)
