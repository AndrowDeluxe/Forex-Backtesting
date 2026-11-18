# Area: Filter-Baustein „Gold-Richtungs-Komposition“

Mehrere Makro-Bausteine stimmen über die Gold-Richtung ab. Ziel des Nutzers (18.11.2026): eine
Komposition verschiedener Filter, die die Richtung mit hoher Wahrscheinlichkeit vorhersagt. Anlass: Der
[[filter-gold-zinskurve]] stand KW46–47 zwei Wochen auf long, während Gold fiel. Plan:
`~/.claude/plans/snoopy-nibbling-whisper.md`. Teil der Schicht „Zinsen“ im Schichtenmodell
([[regime-bestimmung-und-filter]]), für den Makro-Agenten ([[makro-agent-report-pruefung]]).

## Definition

- Code: `fusion_lab/filters/gold_komposition.py` → `GoldRichtungKomposition(z_lag, twist_resets, rule,
  bausteine)`; `votes(day)`, `direction(day)`, `allows(side, day)`, `explain(day)`. Tests
  `tests/test_gold_komposition.py`.
- Bausteine (+1/0/−1, nur Daten vor dem Entscheidungstag): **Z** Zinskurve, **M** Makro-Block wie das
  Live-Veto ([[gold-confirmation-score]]; hier auf GC=F-Tagen ab 2004 nachgerechnet, ab 2013 an 95 % der
  Tage gleiche Stimme), **R2** US-2J fällt, **RR** US-Realzins fällt, **C** COT-Aufbau Non-Commercials.
- Regeln: K1 Mehrheit (Summe ≥ 2), K2 = K1 + Veto durch M oder Z, K3 einstimmig (≥ 3 Stimmen, keine dagegen).
- Neu in `zinskurve_regime.py`: `twist_resets=False` (Twist-Tage unterbrechen die 5-Tage-Bestätigung nicht).
- Neu in `fusion_lab/g8/data.py`: `fetch_fred` lädt nach 20 h automatisch neu (vorher stand der Cache
  unbemerkt Tage zurück).

## Ergebnis Stufe 0 + A (18.11.2026)

Lock `gold_richtung_komposition` (IS 2010–2019, OOS bis 18.05.2026, Blind 2006–2009 registriert, noch zu),
17 Versuche, Skript `scripts/research_gold_komposition.py`, Tabellen `fusion_lab/data/gold_komposition/`.
Kriterium vorab: bei h = 20 in IS **und** OOS besser als „immer long“ und Verschiebungs-p ≤ 0,05 / ≤ 0,10.

- **Stufe 0:** keine Doppelzählung (max. |ρ| 0,56 zwischen R2 und RR). M, RR, C korrelieren 0,3 mit dem
  20-T-Gold-Momentum, Z gar nicht.
- **Stufe A: keine Variante besteht.**
  - Beste im IS: Einstimmigkeit K3 (+3,1…+4,1 bp/Tag gegen „immer long“ +1,3, Trefferquote 57 %), aber
    p 0,06–0,16, also nicht von Zufall zu trennen. Im OOS (Gold-Hausse 2020–26) liegen alle unter
    „immer long“ (+6,3 bp/Tag), weil jede Short-Stimme Geld kostet.
  - **Kürzere Zinskurven-Lags und die Twist-Variante helfen nicht** (Z5/Z10/Z20tf ≈ Z20 innerhalb des
    Rauschens). Die Zinskurve allein hat 2010–2019 keinen Richtungswert (−0,1 bp/Tag, p 0,71). Der frühere
    Beleg (+93 bp/20 T, t 2,16) stammte aus IS 2016–21 und war 1 von 6 Zellen.
  - Einziger Baustein mit IS-Signal ist **M allein** (+5,1 bp/Tag, Treffer 60 %, p 0,03), im OOS aber
    unter „immer long“ (+3,4 vs. +6,3, p 0,14). Das deckt sich mit dem Bild „Makro taugt als Veto, nicht
    als Richtungsgeber“ ([[makro-filter-hilft-edges-nicht]], [[gold-confirmation-score]]).

Lesart: Mehr Bausteine machen die Richtung nicht vorhersagbar. Die Komposition wird wählerischer (K3 nur an
25–35 % der Tage) und meist long, schlägt aber Golds eigene Drift nicht. Offen ist nur die Rolle als
**Veto auf bestehenden Edges** (Stufe B), wo M schon nachweislich hilft (CTNL-Reversal).

## Ergebnis Stufe B: Veto auf Gold-Edges (18.11.2026)

`--stage edges`, Tabelle `stageB_edges.csv`, 36 weitere Versuche (gesamt 53). Kriterium vorab: in IS und OOS
mehr R je behaltenem Trade als mit M allein, und die gesperrten Trades im Schnitt negativ.
**Keine Komposition besteht auf keinem Edge.**

| Edge | M allein: gesperrte Trades IS / OOS | Kompositionen: gesperrte Trades OOS |
|---|---|---|
| CTNL-Reversal live (Ribbon + Spike) | −1,35 R (n 2) / **−0,81 R (n 9)** | **+0,98…+1,75 R** (n 11–28): sperrt Gewinner |
| Gold ASB | +0,41 R (n 31) / +0,41 R (n 32) | +0,28…+0,57 R: sperrt Gewinner |
| Daily-C2 Gold | n 0 / n 2 | n 0–3, zu wenig Trades (16 IS / 13 OOS) |

Lesart: Die zusätzlichen Bausteine (Zinskurve, 2J, Realzins, COT) verwässern das Makro-Veto. Bei CTNL
sperren sie vor allem Reversal-Gewinner, weil ein Gegentrend-Einstieg naturgemäß gegen die Momentum-nahen
Stimmen läuft. Auf ASB hilft weder M noch die Komposition (wie [[makro-filter-hilft-edges-nicht]]). Das
Live-Makro-Veto auf CTNL bleibt die beste Makro-Regel; die Komposition wird nicht eingefroren, Blindtest und
Forward entfallen.

## Noch offen

- Nichts für diese Komposition. Nächster Gedanke (Nutzer 18.11.): wie sich Claude-Makro-Agenten (Screener-
  Pipeline der Aktien/Rohstoffe) auf Gold und Forex schlagen würden; nur vorwärts messbar, siehe Ideen-Inbox.
- Vorgriff: `_vor` und die Regeln sind getestet; `lookahead_guard.check_truncation` wurde nicht angewandt,
  weil `vote_frame` seine Daten selbst lädt (alle Rechnungen schauen nur zurück: diff, rolling, ffill).
