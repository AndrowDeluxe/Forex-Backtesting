# Makro-Datenquellen je G8-Land (Stand 30.10.2026)

Live geprüft beim Bau der Datenschicht `fusion_lab/macro_data/` für den Makro-Agenten
([[quant-diskretionaer-fusion]], Strang 3).

| Bereich | Quelle | Fallstrick |
|---|---|---|
| Leitzins | BIS `WS_CBPOL` | täglich, alle 8 Länder |
| Inflation gesamt | BIS `WS_LONG_CPI` | Australien bei der BIS nur quartalsweise, darum OECD |
| Kern, Dienste, Arbeitslosigkeit, BIP | OECD-SDMX direkt | JP, CH, CA bei Kern/Dienste veraltet; CH und NZ nur quartalsweise |
| Eurozone | Eurostat | `prc_hicp_manr` endet 2025, weiter in `prc_hicp_minr`; `une_rt_m` nur unter `EA21` |
| 2 und 10 Jahre | FRED, EZB (AAA-Kurve) | 2 Jahre nur US und Eurozone; sonst 10 Jahre monatlich |
| Konsens + Ist | Myfxbook-RSS | nur der laufende Tag (GMT): ein Tag ohne Abruf ist verloren |
| Wochenblick | Forex-Factory-Feed | nur laufende Woche, ohne Ist; `nextweek`/`lastweek` geben 404 |
| Positionierung | CFTC TFF + Disaggregated | Berichtsdatum Dienstag, verwendbar erst ab Freitag |
| Fed-Pricing | Yahoo `ZQ*.CBT` | Symbole je Liefermonat; einzelne Kontrakte können fehlen |

**Nicht verwenden:** OECD-Inflationsreihen auf FRED (`CPALTT01*`, `CPGRLE01*`). Sie sind
eingestellt (JP 2022, GB und CA 03/2025) und melden das nicht als Fehler.

**Point-in-time** gilt erst ab dem ersten Abruf am 30.10.2026. Ältere Werte zeigen den heutigen
Revisionsstand. Das Archiv taugt also für den Forward-Betrieb, nicht für Rückrechnungen.
