# Area: Vier-Fragen-Check (jedes neue Edge, jedes neue Paper)

Laufende Verantwortlichkeit ohne Enddatum. Nutzerentscheid 2026-10-18,
übernommen aus der SMH-Elite-Hausaufgabe „Rohling“ bis Call 2 („Vier Sätze
zu deinem Setup. Einer pro Frage.“).

## Die vier Fragen

Je ein Satz, nicht mehr:

1. **Warum verdient es Geld?** Der Mechanismus: wer zahlt die Prämie und
   warum (Risikoprämie, Zwangsfluss, Verhaltensfehler, Mikrostruktur)?
2. **Wo verliert es am meisten?** Die Phasen, Regime, Sessions oder
   Instrumente mit dem größten Teil der Verluste.
3. **Was ist dort anders?** Was die Verlustphasen messbar von den
   Gewinnphasen unterscheidet (Volatilität, Trend, Kalender, Kosten …).
4. **Welche eine Regel könnte helfen?** Genau eine Regel, die die
   Verlustphasen trifft, ohne die großen Gewinnphasen zu verlieren.

## Wann

- **Neues Paper**: in der Sichtung ([[backtest-standard-process]] Phase 2/3,
  [[paper-verarbeitung]] Schritt 2 „Distill“). Frage 1 aus dem Paper selbst;
  Fragen 2-4 aus dem, was das Paper über Verluste/Drawdowns zeigt, sonst nach
  dem ersten Backtest nachtragen.
- **Neues Edge / eigene Strategie**: nach dem ersten Basis-Backtest. Bei
  händischen Strategien ergänzt es die [[edge-card-workflow]] (Frage 1 ≈ Feld
  03 Mechanismus, Frage 2-3 ≈ Feld 04 Gegenprobe).

## Verzahnung mit der Overfitting-Sperre

Fragen 2-4 sind Datenschau auf Verlusten. Damit sie nicht zur Kurvenanpassung
werden ([[overfitting-sperre]]):

- Fragen 2-3 nur auf **IS-Daten** beantworten, nie auf OOS oder Tresor.
- Die Regel aus Frage 4 ist eine **gezählte Variante** (`log_trials`) und
  läuft durch freeze → OOS → Tresor wie jede andere.
- Erfahrung bisher: Regeln, die aus der Bruchphase gelernt wurden, fielen
  durch (ORB, Noise-Area; Memory `regimewechsel_nicht_aus_bruchphase_lernbar`). Eine
  Regel mit klarem Mechanismus aus Frage 1/3 hat bessere Chancen als eine
  rein statistische.

## Ablage

Die vier Sätze stehen am Kopf der jeweiligen Paper-/Projekt-Notiz, Abschnitt
`## Vier Fragen`.
