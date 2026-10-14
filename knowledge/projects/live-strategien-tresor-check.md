# Tresor-Check aller Live-Strategien (Tresor-Variante, 14.10.2026)

**Auftrag (Nutzer, 14.10.):** Die Live-Strategien nach der Tresor-Variante von Dennis
prüfen (letzte 12 Monate = 01.10.2025–30.09.2026 als Holdout, siehe
[[overfitting-sperre]]) und bei negativem Tresor die Hintergründe des Kippens klären.

Skript `scripts/research_live_tresor_check.py`, Zahlen
`ny_open_orb/results/live_tresor_check_beine.csv` und `..._orb_ursachen.csv`.
Quelle: Trade-Listen mit Live-Konfiguration und gemessenen Broker-Kosten
(`scripts/research_live_legs.py`, Stand 04.10.2026).

**Wichtig – vorbelastet:** Mehrere Live-Konfigurationen wurden mit Blick auf 2026
gewählt (CTNL Ribbon/Spike-Filter 09/2026, ORB-Storno 10/2026, Gold-Silber-Livegang).
Das ist ein Gesundheitscheck, kein sauberer Holdout. Ehrliche Prüfung = Forward.

## Ergebnis (Tickmill; TTP/IQ gleiche Richtung)

| Bein | vor 10/2025: n / PF / Ø R | Tresor: n / PF / Ø R / Σ R | Urteil |
|---|---|---|---|
| orb_us30 | 337 / 1,50 / +0,36 | 55 / **0,63** / −0,29 / **−15,9** | **negativ** (seit 04.10. pausiert) |
| btc_ema_cross | 48 / 4,48 / +1,70 | 6 / 0,19 / −0,46 / −2,8 | negativ, aber n = 6 |
| orb_sp500 | 302 / 1,76 / +0,60 | 60 / 1,12 / +0,11 / +6,3 | fast null (t 0,3, DD −21 R) |
| orb_nasdaq (alte Version ohne Storno) | 1.390 / 1,35 / +0,32 | 205 / 1,12 / +0,12 / +23,7 | fast null; heutige Version mit Storno positiv (s. u.) |
| gold_asb | 174 / 2,11 / +0,33 | 29 / 2,07 / +0,18 / +5,3 | positiv, Ø R halbiert |
| ou_modell | 558 / 1,17 / +0,02 | 107 / 1,50 / +0,04 / +4,2 | positiv, dünn wie immer |
| cls_practical | 122 / 1,87 / +0,45 | 18 / 3,36 / +0,81 / +14,6 | positiv |
| ctnl_reversal | 85 / 2,51 / +1,08 | 13 / 2,78 / +1,04 / +13,5 | positiv (Filter 2026 gewählt!) |
| gold_silver | 91 / 2,90 / +1,01 | 13 / 1,95 / +0,58 / +7,6 | positiv |
| trend_pullback | 192 / 1,37 / +0,27 | 32 / 3,18 / +1,00 / +32,1 | positiv |

## Hintergründe des Kippens

**ORB (alle drei Indizes) – gleiche Form:** Verlust je Stop unverändert (−1,05 R), aber
die Trefferquote fällt (S&P 25 → 17 %, US30 32 → 25 %, Nasdaq 14 → 11 %) und Stops
greifen schneller (S&P Median 12 → 8 Min.). Der Ausbruch läuft seltener durch.

Zerlegung der Live-Konfiguration (Research-Simulator, nur 1. Trade je Tag):

| Ø R je Trade | IS 16–22 | OOS 23–09/25 | Tresor |
|---|---|---|---|
| S&P, neutrale Tage (gehandelt) | +0,36 | +0,38 | **+0,08** |
| S&P, Trend-Tage (nicht gehandelt) | −0,27 | −0,21 | +0,15 |
| S&P, Vortag gegenläufig (Kauf nach Minus-Tag) | +0,20 | +0,53 | **−0,09** |
| US30, neutrale Tage (gehandelt) | +0,60 | +0,14 | **−0,53** |
| Nasdaq, neutral / mit Trend / gegen Trend (alle gehandelt) | +0,83 / +0,21 / −0,59 | +0,84 / +0,14 / −0,38 | +0,70 / +1,75 / −1,07 |

1. **S&P:** derselbe Kipp wie bei der IS-only-ORB ([[orb-ribbon-filter-kippt-2026]]):
   neutrale Tage verlieren ihren Vorteil, Trend-Tage werden besser. Dazu verschwindet
   das Umkehr-Muster über Tage (Kauf nach einem Minus-Tag), passend zum marktweiten
   Wechsel Umkehr → Fortsetzung ([[orb-gegenprobe-oel]]).
2. **US30:** kein plötzlicher Kipp, sondern Zerfall seit 2023 (neutrale Tage schon im
   OOS nur +0,14), im Tresor dann negativ. Pause seit 04.10. bestätigt.
3. **Nasdaq:** live ohne Ribbon-Filter, deshalb vom Kipp der neutralen Tage nicht
   getroffen. **Die Broker-Liste rechnet Nasdaq noch in der alten Version ohne
   Storno am geplanten SL** (~206 Trades/Jahr, fast jeder Tag; erzeugt am 04.10.,
   als die Storno-Regel gerade umgestellt wurde). Die heutige Live-Version mit Storno
   (`NASDAQ_RULE = "sl"`, geprüft: 2024 = 77 Trades in beiden Simulatoren) ist im
   Tresor positiv: +0,5 bis +0,7 R je Trade, ~90 Trades. Vorbelastet, weil das
   Storno am 04.10. mit Blick auf 2026 gewählt wurde. Die alte Version ohne Storno
   lag im Tresor bei +0,12 R.
4. **BTC-EMA-Cross:** 6 Trades, davon 2 Stops und 4 kleine Cross-Verluste; 2022
   (−6,5 R) war ein ähnliches Seitwärtsjahr. Kein Beleg für einen Kipp, nur zu
   wenige Trades für ein Urteil.
5. **Gold ASB:** positiv, aber Ø R halbiert (+0,33 → +0,18). Beobachten (Frühwarnung).

## Folgen

- Keine Bot-Änderung aus diesem Check. Kandidaten für eine Entscheidung (Dashboard 🔍):
  orb_sp500 (Filter kippt, Tresor ~0), Nasdaq-Zweit-Trades.
- Die Fälle gehen als Prüfsteine in [[edge-fruehwarnung-kill-switch]].
