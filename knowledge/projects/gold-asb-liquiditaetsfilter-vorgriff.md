# Gold ASB: Liquiditätsfilter sieht den Handelstag (2026-11-01/02)

Verwandt: [[gold-asb-is-only-neuanalyse]], [[gold-asb-kostenvalidierung]].

## Befund
`corwin_schultz_spread` datiert den Wert auf t, nutzt aber Hoch/Tief von t und t+1. Der Filter
liest den Wert vom Vortag, also das Fenster aus Vortag und Handelstag. Der Backtest kennt den
ganzen Handelstag, live sind um 01:00 NY nur rund fünf Stunden davon bekannt.

| 2016–10/2026 | n | Ø R | t |
|---|---:|---:|---:|
| Backtest bisher (Vorgriff) | 273 | +0,308 | 4,20 |
| Live-Wissensstand 01:00 NY | 408 | +0,168 | 2,77 |

## Korrektur unter der Sperre (`gold_asb_liq_fix_20261102`)
Split wie die IS-Neuanalyse (IS 2016–2022, OOS 2023–09/2025, Tresor zu). Drei Varianten vorab,
Quantil 2/3 fest. Skript `scripts/research_gold_asb_liq_fix.py`.

| | IS n / PF / Ø R / t | OOS n / PF / Ø R / t |
|---|---|---|
| V0 Live-Stand | 256 / 1,42 / +0,181 / 2,14 | 114 / 1,34 / **+0,126** / 1,30 |
| **V1 kausal vollständig** (eingefroren) | 192 / 1,67 / +0,266 / 2,64 | 83 / 1,21 / +0,082 / 0,72 |
| V2 Live-Stand, eigene Schwelle | 190 / 1,57 / +0,237 / 2,32 | 81 / 1,03 / +0,016 / 0,13 |

V1 gewann das IS (Deflated Sharpe ≈ 1,00 bei 3 Versuchen) und fiel im OOS hinter den Live-Stand
zurück. Die Korrektur bestätigt sich nicht. Der Live-Filter bleibt unverändert.

Vorbehalt: Das OOS war durch `gold_asb_is_reopt_20261015` schon geöffnet, und die Gesamtzahlen von
V0 waren am 01.11. bekannt. Kein jungfräulicher Test.

## Sollwerte auf Live-Stand (02.11., Nutzerauftrag)
Erwartung = Live-Wissensstand (V0), nicht der Backtest. `pending.live_state_friction` +
`scan_trades(liquidity="live")`:
- Soll/Ist (`scripts/reports/soll_ist.py`): Ø +0,308 → **+0,168 R** (n 273 → 408).
- Edge-Ampel (`research_live_legs.py` → `gold_asb_trades(..., liquidity="live")`): Liste
  +0,309 → **+0,146 R**, Kalibrierfenster 2019–22 +0,365 → +0,164 R. Wirkt ab dem nächsten
  `--ampel`-Lauf; die Drawdown-Schwelle wird dann auf der niedrigeren Basis neu kalibriert.
- Unverändert: Paper-Bots, Live-Orders, Gewichtungs-Skripte (Default `"backtest"`).

## Ausfall-Ersatz
Rückstand 1/2/3 Handelstage: Ø +0,082/+0,058/+0,038 R, t höchstens 1,16
(`scripts/research_gold_asb_stale_filter.py`). Gebaut am 01.11., am 02.11. per
`STALE_FALLBACK_ENABLED = False` abgeschaltet (Nutzerentscheid).

## Soll = Bot-Entscheidung (10.11., Nutzerentscheid)
Die Nachrechnung kann die Live-Entscheidung nicht treffen: Der Lake-Friktionswert für D−1 entsteht um
01:00 NY mit halbem Tag D und wird danach überarbeitet. Beleg mit heutigem Datenstand: 03.11.
Friktion **0,0459** (Schwelle 0,018), also gefiltert. Live wurde Short gelegt (−1.274 USD / −90 EUR).
05.11.: live 0,0314, heute 0,0062.
- `todays_setup()` schreibt je Tag Filterwerte, `friction_date` und Entscheidung nach
  `<Bridge>/logs/gold_asb_filter_journal.jsonl` (EK, Funded, FK; außerhalb von Git).
- `scan_trades(journal=...)` / `soll_ist.py`: An Protokolltagen gilt die Bot-Entscheidung. Der
  Bericht zeigt „Filter-Drift“, also die Tage, an denen die Nachrechnung anders entschieden hätte.
- Handelslogik unverändert. Commit `4c0bcc53`. Ab KW46 vollständig, KW45 und früher weiter nachgerechnet.
