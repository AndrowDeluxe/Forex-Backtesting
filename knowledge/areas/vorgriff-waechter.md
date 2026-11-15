# Area: Vorgriff-Wächter (Abschneide-Test + Engine-Selbsttest)

Seit 2026-11-15 (Nutzerentscheid). Code: `lookahead_guard.py` (Repo-Wurzel),
Tests: `tests/test_lookahead_guard.py`. Gehört zu Phase 4 des
[[backtest-standard-process]], ergänzt die [[overfitting-sperre]]. Die Sperre
schützt vor Auswahl auf ungesehenen Daten, der Wächter vor Code, der in die
Zukunft schaut.

## Warum

Drei Vorgriffe wurden bisher erst spät und von Hand gefunden. Alle drei hätte
der Abschneide-Test automatisch gemeldet (als Regressionstest nachgestellt):

- **ASB-Friktion** (01.11.): `corwin_schultz_spread` datiert auf t, nutzt Hoch/Tief
  von t+1. Ø R sank auf dem Live-Wissensstand von +0,308 auf +0,168.
  Siehe [[gold-asb-liquiditaetsfilter-vorgriff]].
- **Lake-H4-Duplikate** (28.10.): Der Modus der Abstände gab 1 h statt 4 h, also
  wurde jede H4-Kerze 3 h vor ihrem Schluss angehängt.
  Siehe CHANGELOG 28.10. (Lake-Reparatur).
- **CTNL-Risikohalbierung** (30.09.): Die Verlustserie zählte noch offene Vorgänger
  mit. Siehe [[ctnl-kostenvalidierung]].

Anstoß war der AI-Pathways-Kurs aus der YouTube-Sichtung „AI Trading Bot“
(15.11.). Sonst enthielt die Sichtung keinen Edge.

## Wie es funktioniert

**Abschneide-Test** `check_truncation(fn, data)`: Er rechnet `fn` einmal auf allen
Daten. Dann schneidet er an 30 zufälligen Stichtagen die Daten ab, rechnet neu
und vergleicht jede Ergebniszeile bis zum Stichtag. Eine kausale Rechnung kommt
auf dasselbe heraus, jede Abweichung ist ein Vorgriff.

- Mehrere Zeitebenen gehen als dict hinein (`{"h4_df": …, "m15_df": …}`).
- `known_after` sagt, ab wann eine Zeile bekannt ist. Bei Kerzen mit
  Eröffnungs-Stempel ist das die Balkenlänge (`"4h"`, `"15min"`). Falsch
  angegeben testet man etwas anderes.
- Bei Trade-Listen `time_col="entry_time"` setzen und nur Felder vergleichen, die
  beim Einstieg feststehen (`columns=["risk", …]`, nicht `exit_*`). Bei Füllung
  zur nächsten Eröffnung zusätzlich `settle="1D"` (bzw. eine Balkenlänge).
- Bausteine, die absichtlich nach vorn datieren (z. B. Fraktal-Swings, CS-Spread
  nach Paper-Konvention), schlagen erwartungsgemäß an. Prüfen muss man das
  fertige Signal, so wie es live entschieden wird.

**Engine-Selbsttest** `engine_selftest(run_fn)`: Er prüft die Backtest-Engine auf
Kunstdaten. `run_fn(ohlc, signal)` liefert Trade-Renditen.

| Probe | Daten | korrekte Engine |
|---|---|---|
| eingepflanzt | Balken nach jedem Signal +1 % | Ø 0,6–1,2 % minus Kosten |
| rauschen | Zufallspfad, gleiche Signale | Ø ≈ −Kosten |
| signalbalken | +1 % auf dem Signal-Balken selbst | Ø ≈ −Kosten; Gewinn = Füllung vor dem Signal |

## Erster Einsatz an echtem Code (15.11.)

Der CTNL-Signalweg `gold_smc_htf_ltf.reversal_cascade.run_pipeline`
(Standardparameter, Lake-Gold H4/H1/M15 24.08.–13.11.) ist sauber: 12 Stichtage,
31.195 Zeilen, keine Abweichung, 3 s Laufzeit. Die Live-Konfiguration mit Ribbon
(D1/W1-Daten) ist noch nicht geprüft.

Zu `_bar_length` (Fix vom 28.10.): Liegen in einem Datenfenster mehr als 60 % der
Kerzen doppelt vor, gibt auch das 75-%-Quantil zu wenig (3 h statt 4 h). Mit den
reparierten Lake-Daten ist das kein Thema. Der Wächter würde es melden.

## Regel

Vor jeder IS-Auswertung eines neuen Signals oder Filters `check_truncation` auf
die fertige Signalfunktion laufen lassen. Bei einer neuen oder umgebauten Engine
zusätzlich `engine_selftest` ausführen. Schlägt einer an, wird erst repariert,
dann ausgewertet.
