# Resource: CPI/NFP-Ereignisstudie – Regeln aus der Makro Education

Stand 26.11.2026. Prüft vier Regeln aus den OneNote-Seiten „Makro Education“ (ausgelesen 25./26.11. mit
`fusion_lab/inventory/makro_education_extract.py`, Ergebnis `fusion_lab/data/onenote_macro/makro_education_v2/`).
Skript `scripts/research_ereignisstudie_cpi_nfp.py`, Test `tests/test_ereignisstudie.py`, Tabellen
`fusion_lab/data/research/ereignisstudie/`. Verwandt: [[makro-wirkketten-katalog]], [[endogen-exogen-gatekeeping]],
[[remy-king-trading-strategie-top1]] (A3: „nach der Zahl in Überraschungsrichtung“ widerlegt).

Tags: Makro, CPI, NFP, Ereignisstudie, Overfitting-Sperre.

## Aufbau

- Termine: ForexFactory-Historie 2007–11/2026 (Ist/Konsens), Überraschung je Indikator auf die IS-Streuung
  normiert und bei ±3 gekappt (Corona-NFP ergab sonst |z| > 20).
- Reaktion: letzter Kurs vor dem Termin → +60 Min. (M5/M1 ab 2016/2018/2012, davor H1-Kerze: Open der Terminkerze →
  Schluss der Folgekerze). US-2J: Tagesänderung (FRED DGS2). Stichprobe 13.10.22, 10.11.22, 02.08.24 passt zur Geschichte.
- Sperre: Lock `ereignis_cpi_nfp_v1` (IS 2007–18, OOS 2019 – 25.05.2026) und `ereignis_sperre_beine_v1`
  (Beine, IS 2016–21, OOS 2022 – 25.05.2026). Tresor ab 26.05.2026 zu. Kriterium „trägt“: IS t ≥ 2 und OOS gleiche
  Richtung mit t ≥ 1.

## Ergebnis

| # | Regel (Seite) | Urteil |
|---|---|---|
| H1 | CPI bewegt Zinsen/USD stärker als NFP (Blueprint 2024) | **hängt am Regime**: 2007–18 NFP 3–5× stärker, 2021–23 CPI 3–4× stärker, seit 2024 etwa gleich (NASDAQ: CPI bleibt vorn) |
| H2 | Core erklärt die Reaktion besser als Headline (Blueprint, Macro Report 2024) | **hängt am Regime**: 2007–18 Core klar vorn, 2019–26 Headline gleich stark oder stärker (Energie-Inflation); nur Gold besteht |
| H3 | Inflationsüberraschung stärkt die Währung nur ohne Wachstumsschwäche (Top Down 12.05.2024) | **trägt nicht**: 0/6 Varianten; nach der ersten Stunde läuft der Kurs in beiden Gruppen zurück (wie A3); beste IS t −1,3, DSR 0,02 |
| H4 | „Neutral bis Freitag“: Beine verlieren über Termine (Macro Report 20.10.2024) | **trägt nicht**: kein Bein. OU „offen über Termin“ (IS t −2,4, OOS −2,5) ist ein Haltedauer-Artefakt: an Placebo-Tagen gleich (t −2,8 bis −4,2), lange OU-Trades verlieren (ρ R~Dauer −0,52) |

H1 in bp je 1 SD Überraschung (+60 Min.):

| Zeitraum | EURUSD CPI / NFP | USDJPY CPI / NFP | US-2J CPI / NFP | NASDAQ CPI / NFP |
|---|---|---|---|---|
| 2007–18 | −6,9 / −22,1 | +6,3 / +30,2 | +0,1 / +3,0 | −10,0 / +7,3 |
| 2019–20 | +0,7 / −4,2 | −3,4 / +5,2 | −0,9 / +0,7 | −10,6 / +4,4 |
| 2021–23 | −32,5 / −7,9 | +35,5 / +9,4 | +6,0 / +1,4 | −92,2 / −10,6 |
| 2024–05/26 | −22,7 / −20,6 | +40,0 / +26,5 | +5,0 / +5,2 | −41,2 / +1,0 |

## Lesart

- Die Seite „Blueprint 2024“ hatte für ihre Zeit recht, die Regel ist aber nicht zeitlos: **Der Markt reagiert auf
  die Zahl, die das aktuelle Fed-Problem misst.** Kämpft die Fed gegen Inflation (2021–23), dominiert CPI; geht es
  um Arbeitsmarkt und Wachstum (bis 2018), dominiert NFP. Seit 2024 (Doppelmandat wieder ausgeglichen) sind beide gleich.
- **Umgesetzt 26.11.:** Das Fact Sheet (Abschnitt Kalender) misst das Termin-Gewicht laufend aus der 2J-Reaktion der
  letzten 24 Monate (`analytics/event_weights.py`) und hängt es an anstehende US-CPI/NFP-Termine. Stand 26.11.: CPI 63 %.
- Termine liefern Reaktion, keine Drift: Die erste Stunde läuft mit der Überraschung, danach nichts Handelbares –
  auch nicht bedingt auf die Wachstumslage. Kein Grund, die Beine um Termine zu sperren.

## Offene Punkte

- NFP-Monatsketten der Seite „How To NFP Report“ (Wochenstunden Industrie < 40 / ≥ 40,5, Überstunden < 3,
  Dauer der Arbeitslosigkeit, 15+ Wochen Arbeitslose als Frühindikator) → nach dem Nachtauslesen gesammelt in den
  Wirkketten-Katalog (FRED AWHMAN, AWOTMAN, UEMPMEAN, UEMP15OV).
