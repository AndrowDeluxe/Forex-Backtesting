# Optimierte Edges und Tests: Übersicht (Stand 16.10.2026)

Was in der Öl- und Noise-Area-Arbeit vom 11.–16.10.2026 entstanden ist, wo es steht und
wann es geprüft wird. Kein Eintrag ist live. Alle laufen nur als Forward-Test per Skript,
Stichtag **31.03.2027**. Mechanismus: [[oel-als-marktregime]].

## Kandidaten im Forward

| Edge | Regel kurz | Backtest (IS / OOS / Tresor) | Lock | Auswertung |
|---|---|---|---|---|
| **K60 NASDAQ** (Hauptkandidat) | Noise Area, nur 1. Ausbruch 10:00–15:30, bis 16:00 halten; nur bei Korr(Öl, NASDAQ, 60 T.) < 0 | +24,7 / +6,2 / +11,7 bps je Trade; 100k bei 1 %: 128.966 / 106.976 / 113.424 | `noise_area_oel_k60_forward_20261014` | `python scripts/forward_noise_area_k60.py evaluate` |
| **Challenge TTP** | K60 ohne Stop 1 % + ORB-NASDAQ-Öl 0,25 %, max. 2 Trades/Tag | MC +8,2 %/Jahr, P(Bruch) 5 %, P(Ziel 10 %) 46 %; Endstände 161.590 / 116.021 / 126.591 | `challenge_k60_orb_oel_gewichtung_20261016` | `python scripts/research_challenge_k60_orb_gewichtung.py evaluate` |
| **Challenge IQ** | wie TTP, K60 0,75 % | MC +7,1 %/Jahr, P(Bruch) 5 %, P(Ziel 8 %) 53 % | dito | dito |
| **ORB-Öl O1** | ORB nur, wenn Öl 09:00–09:45 gegen die Ausbruchsrichtung lief (IS-validiert, DSR 0,96/0,99) | Ø R S&P +0,41 / +0,25 / −0,68, Nasdaq +0,51 / +0,41 / −0,18 | `orb_oel_filter_is_20261012` | `python scripts/research_orb_oel_filter.py --stage forward-evaluate` |
| **ORB-Öl O2** | Korrelationsregime → Trend-Tage + Öl gegen (an 2026 angepasst, explorativ) | 2026: S&P +39 R, Nasdaq +46 R (DSR ≈ 0) | `orb_oel_filter_fit2026_20261012` | dito |
| K60 SL/TP/Haltedauer | 27 Varianten: kein SL/TP + bis 16:00 bleibt am besten, kürzer halten kostet | kein zusätzlicher Forward | `noise_area_k60_sltp_20261015` | — |
| Öl-Faktor-Fit Noise Area | NASDAQ K2 + Korr. 40 T. < −0,1 + Öl bewegt | Fit +28 bps, 2023–25 −4,9 (überangepasst) | `noise_area_oel_fit2026_20261014` | `python scripts/research_noise_area_oel_fit2026.py evaluate` |
| Noise-Area-Regime-Raster | Fade-Gewinner 10/25–03/26 (OOS/Tresor schon gescheitert) + Kontrollen K1/K2 | OOS −5,9 / −8,4 bps | `noise_area_regime2026_20261014` | `python scripts/research_noise_area_regime2026.py evaluate` |
| SP500-Filter „Öl ruhig“ | Paper-Noise-Area nur bei ruhigem Öl | +3,0 / +0,8 / −1,9 bps | `noise_area_oel_filter_20261014` | `python scripts/research_noise_area_oel.py evaluate` |

## Verworfen (ehrlicher Befund)

- **Paper-Noise-Area (Zarattini) 1:1:** Der Nachbau trifft das Paper, ist aber im Tresor
  durchgefallen (Sharpe −1,29 / −0,62). Siehe [[zarattini-noise-area-momentum]].
- **Breites Raster auf dem Bruch-Halbjahr:** zum zweiten Mal gescheitert, siehe
  Memory „Regimewechsel nicht aus Bruchphase lernbar“.
- **Noise Area direkt auf Öl:** kein Edge.

## Vor einem Livegang zu klären

1. Kann IQ NASDAQ handeln? (`check_symbols.py`)
2. TTP-Kommission auf USTEC (bisher 0 angenommen)
3. Lot-Rundung in der Challenge-Gewichtung prüfen
4. Gegenprobe Simulation gegen live (die Simulation war bisher immer optimistischer als live)
