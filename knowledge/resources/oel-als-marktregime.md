# Öl als Marktregime für US-Index-Intraday-Strategien

Destilliert am 16.10.2026 aus drei Testreihen (11.–16.10.):
[[orb-gegenprobe-oel]] (ORB-Gegenprobe + Öl-Filter) und
[[zarattini-noise-area-momentum]] (Noise-Area-Momentum + Öl). Alle Zahlen sind auf
Dukascopy-CFDs (SP500, NASDAQ, WTI) gerechnet, netto nach gemessenen Kosten,
Perioden IS 2016–22 / OOS 2023–09/25 / Tresor 10/25–09/26.

## Kernaussage

**2026 ist ein Öl-Schock-Regime.** Die rollende Korrelation der Tagesrenditen
Öl ↔ Aktienindex war von 2016 bis 2025 durchgehend positiv (Median SP500 +0,06
bis +0,45). 2026 kippt sie auf **−0,45 (SP500) bzw. −0,32 (NASDAQ)**. Öl steigt,
wenn Aktien fallen (Angebots- oder Inflationsschock statt Nachfrage-Gleichlauf).

Gleichzeitig dämpfen sich die Intraday-Trends **marktweit**:
- Ausbrüche aus der Noise Area halten bis Schluss: NASDAQ 46 → 46 %,
  SP500 43 → 39 %, **Öl selbst 39 → 28 %**.
- Das Tag-zu-Tag-Verhalten dreht bei allen drei Märkten von Umkehr zu
  Fortsetzung (ORB-Gegenprobe).

Weil auch Öl betroffen ist, erklärt das SPX-Dealer-Gamma allein die Dämpfung
nicht ([[gamma-mechanismen-gex]]).

## Mechanismus (Hypothese, gestützt, nicht bewiesen)

Es gibt zwei Arten von Tagen:
1. **Öl-Schock-/Makro-Tage** (Öl läuft gegen Aktien, große Öl-Bewegung):
   Informationen kommen langsam in den Preis, Positionierung muss umgebaut
   werden, Intraday-Trends laufen bis zum Schluss. Unterreaktion wie im
   Zarattini-Paper.
2. **Normale Tage** (Öl und Aktien driften gemeinsam): Ausbrüche laufen eher
   zurück. 2026 sind sie zusätzlich durch hohes Long-Gamma gedämpft (SPX-GEX
   Median 5,8 Mrd. $ statt 2,4).

Ein Momentum-Edge lebt deshalb 2026 nur noch auf Tagen der ersten Art.

## Belege

| Test | Ergebnis |
|---|---|
| ORB auf Öl (11.10.) | kein ORB-Edge, kein Eröffnungsschock (1,5 statt 2,4–3,0 ATR) |
| Noise Area auf Öl (14.10.) | kein Edge (brutto ~0), Tresor-Persistenz 28 % |
| Noise-Area-Trades nach Korrelation (Tresor) | K20 < −0,2: SP500 +2,7, NASDAQ +9,5 bps; K20 ≥ 0: −4 bis −9 bps |
| Noise-Area-Trades nach Öl-Tagesbewegung | starke Öl-Tage in jeder Periode am besten (NASDAQ Tresor +9,9 bps; Lookahead) |
| Öl gegen Ausbruchsrichtung | im IS besser (ORB DSR 0,96/0,99; Noise Area 12,1 statt 5,0 bps), im Tresor ohne Wirkung |
| **NASDAQ Noise Area K2 + Korr. 60 T. < 0** | **+24,8 / +6,2 / +11,7 bps je Trade**, einziger Faktor, der in allen drei Perioden trägt |

Nicht tragend: Öl-Gap, Öl-Volatilität, Öl-5-Tage-Trend, „Öl ruhig“ (nur SP500
leicht besser).

## Was daraus gebaut wurde (alles nur im Forward bis 31.03.2027)

- **K60** (`scripts/forward_noise_area_k60.py`): NASDAQ, erster Noise-Area-
  Ausbruch, halten bis 15:55/16:00, nur bei Korr(Öl, NASDAQ, 60 T.) < 0.
  100k bei 1 % Risiko: 128.966 / 106.976 / 113.424.
- **ORB-Öl O1/O2** (`scripts/research_orb_oel_filter.py`): O1 = IS-validiert
  („Öl gegen“), O2 = an 2026 angepasst.
- **Challenge-Gewichtung** (`scripts/research_challenge_k60_orb_gewichtung.py`):
  TTP K60 1 % + ORB-NASDAQ 0,25 %, IQ K60 0,75 % + ORB-NASDAQ 0,25 %.

## Grenzen

- **Vorbelastet:** Die K60-Regel wurde nach Sicht auf alle Perioden gewählt.
  Erst der Forward entscheidet.
- **Seltenes Regime:** 2018–2021 war die Korrelation fast nie negativ, K60
  hatte dort kaum Trades. Dreht das Regime zurück, wird der Filter still,
  er erzeugt dann keine Verluste.
- Öl-Kosten (4,75 bps) sind angenommen, die Index-Kosten gemessen.

## Prüfregel für neue Index-Intraday-Ideen

Vor jedem Weiterbau die Trades nach der Öl-Index-Korrelation (20/60 Tage, bis
Vortag) aufteilen. Trägt ein Edge 2026 nur bei negativer Korrelation, ist er ein
Regime-Edge und kein Allzeit-Edge. Dann Gewicht und Erwartung danach ausrichten.
