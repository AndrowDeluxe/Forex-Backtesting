# ORB-Gegenprobe mit Öl (WTI): welcher Mechanismus?

**Status: gerechnet 11.10.2026** (Hinweis aus der Mentor-Gruppenarbeit: „Daten mit
Öl abgleichen, welchen Mechanismus verfolgt Öl gegenüber S&P/Nasdaq“).
Vorgeschichte: [[orb-order-storno-und-haltedauer]] (IS-only-ORB, Tresor
durchgefallen) und [[orb-neues-regime-2026]]. Prozess: [[overfitting-sperre]].

## Aufbau

- Skript `scripts/research_orb_oel_vergleich.py`, Lock `orb_oel_vergleich_20261011`
  (gleicher Split wie IS-only, 8 Versuche gezählt, eingefroren, OOS + Tresor je
  einmal geöffnet).
- Keine Optimierung: 4 feste Konfigurationen (SP500-Gewinner, NASDAQ-Gewinner,
  ungefiltert, mit Trend) × 2 Uhren (Index 09:30–16:00, Öl 09:00–14:30).
- Kosten Öl: **Annahme** 4,0 bps Spread + Index-Slippage (~0,15 R je Trade).
  April 2020 (WTI nahe null) ausgelassen. Öl-Daten enden 29.09.2026.
- Kontrolle: SP500 reproduziert die PDF exakt (569 / PF 1,41 IS, Tresor −53,9 R).
- Ergebnisse: `ny_open_orb/results/oel_vergleich_*.csv`, Log `oel_vergleich_run.log`.
- PDF: `Claude outputs/orb_profitabilitaets_kriterien_oel_20261011.pdf` (Original-
  10 Seiten + 3 Öl-Seiten, Generator `Claude outputs/orb_pdf_build/orb_pdf3_oel.py`).

## Befund

| Messung | S&P 500 | Nasdaq 100 | Öl |
|---|---|---|---|
| Bester ORB in IS (PF / t) | 1,41 / 2,8 | 1,60 / 3,5 | 1,03 / 0,3 |
| 1. 15-Min-Kerze in ATR (IS) | 2,4 | 3,0 | 1,5 (Öl-Uhr 1,8) |
| Folgequote 1. Ausbruch | 50 % | 52 % | 51 % |
| Trendfilter-Spread IS / OOS / Tresor | +0,48 / +0,46 / −0,65 | +0,35 / +0,41 / −0,41 | +0,09 / +0,17 / +0,01 |
| Tag-zu-Tag-t IS → Tresor | −1,4 → +0,8 | −2,5 → +1,0 | −0,7 → +1,7 |
| Korrelation Sitzung Öl↔S&P IS → Tresor | | | +0,23 → −0,21 |

1. **Öl hat keinen ORB-Edge**, zu keiner Uhrzeit, in keiner Konfiguration. Brutto
   +0,04 bis +0,18 R, die Kosten fressen das.
2. **Öl hat keinen Eröffnungsschock.** Bei den Indizes ist die erste Kerze 2,4–3,0
   ATR breit, bei Öl 1,5. Schock und Edge treten zusammen auf: indirekte Stütze
   für Feld 1 (Auktion/Zwangsflüsse zur Eröffnung), nicht kausal.
3. **Der Trendfilter-Kipp 2026 ist index-spezifisch.** Bei Öl war der Filter nie
   stark (Rauschen ±0,2 R) und kippt nicht deutlich.
4. **Marktübergreifend dreht das Tag-zu-Tag-Verhalten** von Umkehr (bis 2025, 2025
   besonders stark) zu Fortsetzung (2026), bei allen drei Märkten gleichzeitig,
   obwohl Öl und S&P im Tresor gegenläufig laufen. Einzeln nicht signifikant.
   Lesart (Hypothese): Der Index-ORB-Edge auf „neutralen Tagen“ lebte von einem
   Umkehr-Regime über Tage, und genau das ist 2026 marktweit weg.
5. Intraday-Momentum nach Gao ist in keinem der drei Märkte messbar (eher Umkehr).
   EIA-Mittwoch bei Öl: kein stabiler Effekt (IS +0,09, OOS −0,37, Tresor +0,10 R).

## Offen

- Lesart 4 prüfen: Hängt der ORB-Edge auf neutralen Tagen am Tag-zu-Tag-
  Umkehr-Regime? Testbar auf weiteren Märkten (DAX, Gold) als frische Daten.

## Öl als Filter (12.10.2026, Nutzerauftrag)

Skript `scripts/research_orb_oel_filter.py`. Basis: eingefrorene IS-only-7p-ORB.
Merkmale (alle vor 09:45 bekannt): Korrelation Öl↔Index (bis Vortag), Öl-Autokorrelation,
Öl-Rendite 09:00→09:45 gegen/mit der Ausbruchsrichtung. Ergebnisse `ny_open_orb/results/oel_filter_*`.

**Option 1 – nur IS (Lock `orb_oel_filter_is_20261012`, 16 Versuche):** Je Index erfüllt nur
„nur handeln, wenn Öl 09:00–09:45 gegen die Ausbruchsrichtung lief“ die Kriterien; die
Korrelations-Regeln (Hauptthese) machten es schon in IS schlechter.

| | IS Ø R | OOS Ø R | Tresor Ø R (vorbelastet) |
|---|---|---|---|
| S&P Basis / + Öl-Filter | +0,33 / +0,41 | +0,32 / +0,25 | −0,48 / −0,68 |
| Nasdaq Basis / + Öl-Filter | +0,45 / +0,51 | +0,22 / +0,41 | −0,36 / −0,18 |

→ Rettet den Tresor nicht. Nasdaq-Hinweis (OOS besser, Tresor-Verlust halbiert) bleibt dünn.

**Option 2 – an 2026 angepasst (Lock `orb_oel_filter_fit2026_20261012`, 1.524 Versuche,
EXPLORATIV, KEIN BELEG):** Gewinner beider Indizes: Korrelation Öl↔Index (20 Tage) unter
+0,2 (S&P) bzw. 0 (Nasdaq) → Trend- statt neutrale Tage, plus Öl gegen den Ausbruch.
2026: S&P +39 R (PF 2,04, 50 Trades), Nasdaq +46 R (PF 2,23, 53 Trades); Deflated Sharpe
≈ 0. Rückblick: Nasdaq-Regel 2016–25 unschädlich (+0,33 / +0,31 R), S&P-Regel schwächer
als die Basis (2023–25 +0,10 statt +0,32 R).

**Forward:** beide eingefrorenen Varianten ab 12.10.2026, Auswertung frühestens
31.03.2027 (`--stage forward-evaluate`). Kein Livegang.
PDF: `Claude outputs/orb_profitabilitaets_kriterien_oel_20261012.pdf` (15 Seiten).
