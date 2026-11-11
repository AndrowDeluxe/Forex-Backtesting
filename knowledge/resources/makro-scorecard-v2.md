# Resource: Makro-Agent v2 – Multi-Faktor-Scorecard und Ersatzquellen

Umbau des Makro Fact Sheets nach dem Nutzerauftrag vom 11.11.2026 („Makro-Agent auf Banken- und
Hedgefonds-Niveau, fehlende Parameter aus anderen Quellen“). Vorlauf: [[makro-gates-evidenz]].
Gehört zu [[quant-diskretionaer-fusion]] (Strang 3), Prüf-Ablauf in [[makro-agent-report-pruefung]].

Tags: Makro, Scorecard, Carry, Momentum, Value, COT, Fed-Pricing, Agent.

## Aufbau (Code `fusion_lab/macro_agent/`)

| Ebene | Inhalt | Datei |
|---|---|---|
| Strategisch (1–3 M) | 5 Faktoren je Währung als Querschnitts-z, gleich gewichtet: Carry (Leitzins), Zins-Momentum (Δ 2J, 3 M), Preis-Momentum (12-1 M + 3 M), Value (−REER gegen 10-J-Mittel), Überraschungen (60 T, Stil Citi-ESI). Veto bei COT 3 J ≥ 90 / ≤ 10 | `factors.py`, `panels.py` |
| Taktisch (Woche) | Fed je Sitzung aus Futures (CME-Methode), andere Notenbanken 1J − Leitzins, Rohstoff-Schalter (Kupfer/Brent 105/Milch) | `fed_meetings.py`, `tactical.py` |
| Risiko | gleiche Risikoeinheit je Idee (Vol 20 T), Netto-Exposure je Währung, Deckel 1,5 | `risk.py` |
| Zustand | TAIL bei 2 von VIX/HY/Brent/OAT-Bund oder St.-Louis-Stressindex > 1 | `analytics/state_machine.py` |
| Ansicht | Gates R (Carry + Zins-Mom.) / P (Preis-Mom.) / F (Veto), M = Agent | `analytics/gates.py` |

Aufruf: `python -m fusion_lab.macro_agent [--as-of DATUM] [--notion]`.

## Ersatzquellen (11.11. live geprüft)

| Lücke | Ersatz |
|---|---|
| Leitzins hinkt (BIS) | Zinsentscheid-Ist aus dem Kalender (FF-Historie ab 2007 + Live); US/EA nicht (Kalender meldet Obergrenze bzw. Hauptrefi-Satz), EA über täglichen Einlagensatz (FRED) |
| US-2J hinkt (FRED) | TradingView US02Y; AU-2J (RBA ~1 Woche) über TradingView AU02Y |
| Pricing ohne OIS | 1J-Renditen: TradingView, MoF, EZB, SNB |
| Kern-Inflation JP/CA/CH | Kalender (National Core CPI, Trimmed CPI), SNB-Würfel `plkoprinfla` (K1) |
| US-Dienste-Inflation | FRED `CUSR0000SASLE` (Jahresrate gerechnet) |
| OAT-Bund, Stress | TradingView FR10Y − DE10Y; FRED `STLFSI4` |
| Rohstoffe, Value | Yahoo HG=F / DC=F; BIS REER (breiter Korb) |

Ersatzreihen tragen den Schlüssel `<Land>.<Größe>@<Quelle>` und verlängern die Hauptreihe nur nach
deren letztem Datum (`fusion_lab/macro_data/calendar_values.extend`), damit nichts überschrieben wird.

## Prüfung gegen öffentliche Quellen (11.11.)

- Fed Dezember: vor CPI 83 % (CME FedWatch 84 %), nach CPI 27,5 bp erwartet (FedWatch 90,5 % × 25 +
  9,5 % × 50 = 27,4 bp). Nach Regel 3.1 war der Schritt schon vor der Zahl „bezahlt“.
- BoE 4,00 %, RBA 4,85 %, US-2J 4,75 % am CPI-Tag: stimmen mit Notenbank- und Pressemeldungen.

## Backtest (Lock `macro_scorecard_v1`, `scripts/research_macro_scorecard.py`)

Kandidat vorab festgelegt: Score + Veto + Regime, long Top-2 / short Bottom-2, Monatsende, Kosten
(Spread, Swap-Aufschlag) und Carry eingerechnet. 8 gezählte Rechnungen.

| Variante | IS 2007–16 Sharpe (t) | OOS 2017–05/26 Sharpe (t) |
|---|---|---|
| V3 Kandidat | −0,27 (−0,87) | −0,21 (−0,65) |
| V1 Score ohne Veto | −0,09 | −0,41 |
| nur Carry | 0,13 | 0,12 |
| nur Zins-Momentum | −0,39 | −0,45 |
| nur Preis-Momentum | −0,19 | −0,61 (t −1,90) |
| nur Value | 0,07 | −0,62 (t −1,92) |
| nur Überraschungen | −0,29 | 0,22 |

- **Kein Edge.** Kein Faktor kommt in beiden Zeiträumen über t 0,5; Veto und Regime senken nur den
  Drawdown (OOS −37 % → −24 %). Tresor bleibt zu (kein Livegang).
- Preis-Momentum dreht nach 2016 ins Negative. Gegenprobe direkt an Rohkursen (3-M-Rang gegen
  Folgemonat): IC 2007–16 +0,04 (t 1,0), 2017–26 −0,07 (t −1,66), also kein Vorzeichenfehler.
- Deckt sich mit Literatur (G10-Faktoren nach 2008 schwach) und mit den Remy-Tests (Carry OOS −0,18).
- **Folge:** Die Scorecard ordnet im Fact Sheet die Makrolage, gibt aber keine Richtung vor. Offen als
  nächste Prüfung: Scorecard als Filter für C2 (wie der Zins-Momentum-Filter, OOS +0,50 R).

## Fallstricke beim Bau

- Point-in-time nach Abrufzeit im Backtest schloss alle am 11.11. erstmals geladenen Reihen aus
  (Value fehlte ganz); Backtest jetzt mit `point_in_time=False`, Vorgriffsschutz über Bekanntgabe-
  Verschiebungen (REER +45 T, COT Freitag, Werte bis Vortag).
- Legacy-COT (alle Non-Commercials) und TFF-Leveraged-Funds können gegensätzlich stehen (AUD 11.11.:
  0 gegen 82). Das Fact Sheet nennt beide getrennt.
