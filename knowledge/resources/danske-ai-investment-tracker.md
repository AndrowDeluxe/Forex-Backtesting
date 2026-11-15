# Resource: Danske Bank „AI Investment Tracker“ (19.10.2026) – Wirkketten geprüft

Quelle: Danske Markets, AI Investment Tracker, 84 Seiten, Daten bis 16.10.2026, Marketing-Kommunikation
(kein unabhängiges Research, Danske ist Marktmacher). Geprüft am 15.11.2026 auf Nutzerauftrag („Wirkketten
auf Funktion und Richtigkeit testen, auch deine Annahmen“). Skript `scripts/research_ai_wirkketten.py`,
Lock `ai_wirkketten` (IS 2004–2017, OOS 2018 – 15.05.2026, Tresor 16.05.–13.11.2026 zu, 20 gezählte Versuche).
Gehört zu [[makro-wirkketten-katalog]] und [[quant-diskretionaer-fusion]] (Makro-Agent).

Tags: Makro, KI-Boom, Wirkkette, Kredit, AUD, Nasdaq, Gold, Inflation.

## Kernaussagen des Reports (kurz)

- Basisfall „Boom läuft weiter, Herausforderungen nehmen zu“. Investitionen und Nachfrage stehen auf grün,
  Engpässe, Kredit und Politik auf gelb bis orange.
- Investitionen der US-Hyperscaler: ~450 Mrd. USD (2025) → ~890 Mrd. (2026e) → ~1.200 Mrd. (2027e).
- Engpässe: Speicherchips (DRAM ~10× gegenüber 2025, Höhepunkt 2027/28), Packaging, Stromnetz, Genehmigungen.
  Chinas Exportpreise +15,1 % J/J, nach Danske wegen der Speicherchips.
- Aktien: Halbleiter und Hardware vorn, Software hinten. „Profiteure schlagen Investoren.“ IT-KGV 17
  (Schnitt 18,5). Der freie Cashflow der Hyperscaler ist 2026 negativ (−151 Mrd. USD).
- Kredit: Rekordemissionen. Spreads von Oracle ~280 bp und CoreWeave ~1.000 bp. Die Finanzierungslücke ist 2027 am größten.
- Politik: KI-Sicherheitsvorfälle, lokaler Widerstand gegen Rechenzentren. Es stehen Mega-Börsengänge an
  (Anthropic, OpenAI) und die Indexkonzentration ist hoch (Mag 10 = 40,7 % des S&P).
- Interne Widersprüche im Report:
  - Investitionswachstum 2027: +35 % (S. 9) gegenüber +50 % (S. 30)
  - Anteil am US-Aktienmarkt: 44 % gegenüber 40,7 %
  - Anstieg der Finanzierungskosten: „+0,5 %“ im Text, laut Grafik ~0,8 Prozentpunkte
  - Auf S. 10 steht noch eine dänische Entwurfsnotiz

## Getestete Wirkketten (eigene Rechnung)

Spalte „Vorlauf“ heißt: Ist der Messwert bekannt, bevor der Markt sich bewegt? Nur dann ist er handelbar.
Monatswerte wurden mit Veröffentlichungs-Lag gerechnet (Monat m wirkt erst auf die Rendite in m+2).

| Kette (Report / meine Annahme) | Gleichlauf | Vorlauf | Urteil |
|---|---|---|---|
| China-Importpreise (FRED CHNTOT) → US-Kern-Güter-CPI in 6 M | – | IS r −0,15 (t −0,6), OOS r +0,50 (t 2,8); ohne 07/2020–2022 nur t 1,65 | ≈ Kette existiert nur in der Corona-Inflationswelle sicher |
| China-Importpreise → US-2J im Folgemonat | – | IS t −1,3, OOS t −0,5 | ✗ |
| China-Importpreise → Gold im Folgemonat | – | t −0,1 / −0,4 | ✗ |
| Fed-Kanal Gold ~ US-2J (Kontrolle) | IS t −2,9, OOS t −4,1 | – | ✓ Kanal da, aber erst ab dem Zins |
| Korea-Exporte → AUD / Nasdaq | AUD r 0,00 / 0,04, NDX r 0,10 / 0,02 | alle \|t\| < 1 | ✗ auch gleichzeitig kein Zusammenhang |
| Kredit-Spread (BAA10Y) → Nasdaq/AUD Folgewoche | NDX IS r −0,31, OOS r −0,43 (t −7,8) | NDX t −1,3 / −0,2; AUD t −1,6 / −0,4 | ✗ als Frühwarnung |
| Gegenrichtung: Nasdaq → BAA10Y Folgewoche | – | IS t −3,1, OOS t −2,9 | **Aktien laufen vor dem Spread, nicht umgekehrt** |
| HYG/IEF → Nasdaq Folgewoche / 4-Wochen-Blöcke | NDX r −0,69 / −0,57 | t +0,2 / +1,1; 4W-BAA t −0,5 / +0,9 | ✗ |
| Kette `ki_schulden_hy` 1:1 (HY +25 bp in 20 T, VIX < 20 → NDX 20 T) | – | FRED-HY erst ab 11/2023: 6 Signale, Ø +0,25 % vs. Basis +1,89 % | ? zu kurz |
| dieselbe mit Ersatz HYG/IEF 20 T < −2 %, VIX < 20 | – | IS 26 Signale Ø −0,56 % vs. +1,00 % (t −1,4); OOS 10 Ø −0,58 % vs. +1,37 % (t −1,2) | ≈ Richtung stimmt in IS und OOS, nicht signifikant |
| Kupfer → AUD im Folgemonat | – | IS t +0,8, OOS t −1,6 | ✗ |
| Mega-IPO-/Aufnahmetage = unruhige Index-Tage | 6 Fälle (FB, BABA, UBER, TSLA, RIVN, ARM): \|NDX\|-Perzentil 5–84 %, Median ~27 % | – | ✗ keine Unruhe am Ereignistag |

### AUD-Kopplung je Periode (Wochenkorrelation, Gleichlauf)

| Periode | AUD~Kupfer | AUD~Nasdaq | AUD~KOSPI |
|---|---|---|---|
| 2004–2012 | +0,62 | +0,61 | +0,62 |
| 2013–2019 | +0,34 | +0,19 | +0,29 |
| 2020–2022 | +0,51 | +0,51 | +0,65 |
| 2023–2024 | +0,47 | +0,45 | +0,54 |
| 2025–05/2026 | +0,34 | **+0,21** | **+0,54** |

Seit 2025 läuft der AUD kaum noch mit dem Nasdaq, wohl aber mit dem KOSPI (Korea, Speicherchips). Die
„Tech“-Seite des AUD-Schalters läuft im KI-Boom über Asiens Chipbörsen, nicht über die US-Tech-Werte.
Das ist nur Gleichlauf, kein Signal.

## Faktencheck gegen offene Daten

- **✓ Korea-Exporte J/J:** +32 % (01/26) → +68 % (08/26). Der Exportboom aus dem Report stimmt.
- **≈ „China-Exportpreise +15 %“:** Bei den USA kommen davon nur **+3,2 %** an (US-Importpreise aus China,
  09/26). Dahinter steckt aber ein Umschwung von −2,4 % (02/26). Die +15 % sind Chinas eigener Zollindex.
  Speicherchips machen in den US-Importen aus China wenig aus.
- **✗ Breiter Kreditstress:** BAA10Y lag 10/2025 bei 1,68 % und liegt 10/2026 bei 1,44 %, ist also enger geworden.
  Der Kreditstress betrifft nur einzelne KI-Firmen (Oracle, CoreWeave), nicht den Markt.
  Meine Annahme „Spreads als Risk-off-Frühwarnung“ war zu breit.
- **✓ Steigende Zinsen:** Die Laufzeitprämie 10J ging von +0,45 % (10/25) auf +1,00 % (10/26), US-2J von 3,50 auf
  4,77 %. Das passt zu Danskes Finanzierungskosten-Argument. Ob die Emissionen die Ursache sind, ist hier nicht prüfbar.
- **≈ US-PPI Halbleiter:** −2,7 % J/J (10/26). Der Speicherpreis-Boom zeigt sich nicht in den US-Erzeugerpreisen.
- **≈ Megacap-Quartalszahlen:** Sie stehen im Kalender (`fusion_lab/macro_data/earnings.py`), aber **ohne
  ORCL und MU**, also genau ohne die KI-Kredit- und Speicherchip-Werte des Reports.

## Was uns weiterbringt

1. **AUD-Schalter genauer:** Für die Tech-Seite des AUD auf KOSPI und Speicherchip-Werte schauen, nicht auf den
   Nasdaq. Das ist eine Ergänzung zur Leitlinie in [[makro-agent-report-pruefung]] Punkt 3.
2. **Kette `ki_schulden_hy` abschwächen:** Bedingungslos läuft Kredit nicht vor den Aktien, eher umgekehrt.
   Nur bei ruhigem VIX zeigt die Richtung schwach in die erwartete Richtung (t −1,4 / −1,2). Die FRED-HY-Reihe
   reicht nur drei Jahre zurück, HYG/IEF ist der bessere Messwert.
3. **Mega-IPOs sind kein Pausengrund für ORB:** Kein historischer Ereignistag war auffällig.
4. **Inflationsseite:** Die US-Importpreise aus China sind von −2,4 auf +3,2 % gedreht. Das ist Kontext für die
   Zins- und Güterinflations-These, kein Handelssignal (Vorlauf für 2J und Gold fehlt).
5. **Kalender-Lücke:** ORCL und MU fehlen in der Megacap-Liste.

Nicht weiter verfolgen: Korea-Exporte als Schalter, Kupfer-Vorlauf für AUD, Kredit-Spread als
bedingungslose Frühwarnung, IPO-Tage als Risiko für die Index-Beine.
