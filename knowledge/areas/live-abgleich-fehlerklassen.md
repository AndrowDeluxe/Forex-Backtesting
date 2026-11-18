---
title: Live-Abgleich — Fehlerklassen und Prüfmethode
datum: 2026-11-18
status: aktiv, Nutzerauftrag 18.11.2026
---

# Live-Abgleich: Fehlerklassen und Prüfmethode

Anlass war der 18.11.2026. Die NASDAQ-ORB-Bridge hat seit Oktober Tage ausgelassen, an denen der Ausbruch vor der Platzierung kam,
darunter der 09.11. mit +6 R. Das ist wochenlang niemandem aufgefallen. Die Analyse steht in [[orb-nasdaq-kerzen-sl-market]].
Hier steht die allgemeine Lehre, damit das nicht wieder passiert.

## Fehlerklasse 1: Stille Zuordnungslücke

Ein Prüfwerkzeug ordnet Live-Daten über einen Schlüssel zu. Der Schlüssel ändert sich, und danach fällt jeder Fall in denselben Topf.

- **Beispiel:** `soll_ist.py` matchte über `Bein|Einstiegsminute`. Seit dem Umbau auf ruhende Orders (17.09.) haben die ORB-Keys nur noch
  ein Datum (`orb_nasdaq_NASDAQ_PENDING_<Datum>_L_F`). Deshalb stand jeder ORB-Trade als „nie gesehen“, auch der real gehandelte
  +17,9-R-Tag vom 05.11.
- **Warum gefährlich:** Eine Lücke, die jede Woche gleich aussieht, wird zur Hintergrundfarbe. Die echten Verpasser gehen darin unter.
- **Schutz:** `soll_ist.py::matching_warnings()` warnt, wenn ein Bein ≥ 3 Soll-Trades und Ist-Deals hat, aber 0 Treffer. Der Weekly Report
  liest diese Warnungen zuerst (`weekly_report_prompt.md`, Schritt 5).
- **Regel:** Wer State-Keys oder den Order-Pfad einer Bridge ändert, prüft im selben Zug die Zuordnung in `soll_ist.py`.

## Fehlerklasse 2: Backtest füllt dort, wo live noch keine Order liegt

Der Backtest legt seine Order zum Zeitpunkt X. Live liegt sie erst bei X + Latenz. Hängt der Edge an genau diesem Fenster, ist er live
nicht erreichbar.

- **Beispiel:** Bei NASDAQ-ORB (0,6 ATR + Storno) füllen 655 von 702 Backtest-Trades in der ersten Minute nach 09:45 NY. Die Bridge
  platziert erst ~09:45:03 und meldete sonst `breakout_passed`.
- **Prüfung bei jeder neuen Live-Regel:** In welcher Minute füllt der Backtest? Liegt die Live-Order dann schon? Dazu den Backtest einmal
  mit „erste Minute blind“ rechnen. Bleibt wenig übrig, braucht die Regel einen Rückfall (seit 18.11.: Market-Einstieg) oder ist live
  nicht handelbar.

## Fehlerklasse 3: Das Soll misst etwas anderes als live

- Das Soll rechnet auf M5-Lake-Daten. Am 13.11. zeigt es +8,5 R, auf M1 war es −1 R. Ob ein verpasster Tag teuer war, entscheidet
  erst ein Nachrechnen auf M1.
- Siehe auch die älteren Fälle in der Memory „Soll/Ist misst nicht, was es behauptet“ (stilles Überspringen von Beinen,
  Entry- und Exit-Fenster verschieden, Abzugsfehler als 0 Deals).

## Prüfmethode (bewährt am 18.11.)

1. **Backtest je Tag:** Je Live-Tag Richtung, Füll-Minute und R auf M1 (Skript-Vorlage im Scratchpad vom 18.11.:
   `erste_minute.py`, Logik in `scripts/research_orb_nasdaq_kerzen_sl_market.py::trade_day`).
2. **Bridge-Logs je Tag:** platziert / gefüllt / storniert / `breakout_passed` / „keine Log-Zeile“ (Bridge aus).
3. **Abgleichen** in vier Klassen: getroffen, verpasst wegen Latenz, verpasst weil Bridge aus, live ohne Backtest-Gegenstück (meist
   Feed-Unterschied). Für jede Klasse R summieren.
4. **Erst dann** über Regeländerungen reden, mit Lock und IS/OOS, wie in der Overfitting-Sperre.

Verwandt: [[paper-bot-zu-live-bridge]], [[bein-matrix-ist-soll-paper]], [[orb-order-storno-und-haltedauer]].
