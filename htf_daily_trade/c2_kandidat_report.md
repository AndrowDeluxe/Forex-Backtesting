# C2-Kandidat: ausführlicher Backtest (11.11.2026)

Regeln: {'setup': 'C2 EL (Limit 50 % Ausloese-Schluss/Strukturstop, 3 Tage), Sweep 7 Tage, 3 Vorkerzen, MA 12/20', 'filter': {'T6': 'Faber 10 Monate GEGEN die Trade-Richtung', 'M7': 'COT-Fluss Non-Commercials 4 Berichte MIT', 'RS': 'Rohstoff-Veto 20 Tage (AUDUSD~Kupfer, USDCAD~Oel)'}, 'stop': 'S1 Struktur', 'ausstieg': '10 Handelstage', 'be': None, 'teilgewinne': None, 'risiko': 'fest je Trade', 'maerkte': ['AUDUSD', 'EURUSD', 'GBPUSD', 'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY', 'XAGUSD', 'XAUUSD'], 'parameter': 10}

## Kosten-Szenarien (R je Trade nach Kosten)

| Szenario | Periode | n | Ø R | t | Treffer | PF | Σ R | Ø Gewinn | Ø Verlust | bester | schlechtester | max. Verlustserie | max. DD (R) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ohne Swap (bisher) | IS | 120 | 0.618 | 3.118 | 0.450 | 2.146 | 74.139 | 2.571 | -0.980 | 7.415 | -1.194 | 6 | -8.415 |
| ohne Swap (bisher) | OOS | 58 | 0.439 | 1.711 | 0.431 | 1.788 | 25.434 | 2.309 | -0.978 | 7.075 | -1.053 | 6 | -6.068 |
| ohne Swap (bisher) | gesamt | 178 | 0.559 | 3.557 | 0.444 | 2.027 | 99.573 | 2.488 | -0.980 | 7.415 | -1.194 | 6 | -8.415 |
| Swap Tickmill | IS | 120 | 0.604 | 3.052 | 0.450 | 2.114 | 72.480 | 2.547 | -0.986 | 7.529 | -1.216 | 6 | -8.404 |
| Swap Tickmill | OOS | 58 | 0.438 | 1.696 | 0.431 | 1.784 | 25.399 | 2.312 | -0.982 | 7.446 | -1.108 | 6 | -6.192 |
| Swap Tickmill | gesamt | 178 | 0.550 | 3.493 | 0.444 | 2.004 | 97.879 | 2.473 | -0.985 | 7.529 | -1.216 | 6 | -8.404 |
| Swap TTP | IS | 120 | 0.548 | 2.807 | 0.450 | 1.979 | 65.737 | 2.460 | -1.017 | 7.396 | -1.242 | 6 | -8.801 |
| Swap TTP | OOS | 58 | 0.396 | 1.554 | 0.414 | 1.695 | 22.992 | 2.337 | -0.973 | 7.323 | -1.135 | 6 | -6.337 |
| Swap TTP | gesamt | 178 | 0.498 | 3.209 | 0.438 | 1.885 | 88.729 | 2.422 | -1.002 | 7.396 | -1.242 | 10 | -8.961 |
| Stress (Spread×2 + TTP-Swap) | IS | 120 | 0.512 | 2.617 | 0.450 | 1.880 | 61.411 | 2.430 | -1.058 | 7.360 | -1.436 | 6 | -9.390 |
| Stress (Spread×2 + TTP-Swap) | OOS | 58 | 0.376 | 1.472 | 0.414 | 1.644 | 21.787 | 2.318 | -0.996 | 7.305 | -1.145 | 6 | -6.514 |
| Stress (Spread×2 + TTP-Swap) | gesamt | 178 | 0.467 | 3.005 | 0.438 | 1.803 | 83.199 | 2.395 | -1.036 | 7.360 | -1.436 | 10 | -9.390 |
| brutto (ohne alle Kosten) | IS | 120 | 0.654 | 3.304 | 0.458 | 2.265 | 78.465 | 2.554 | -0.954 | 7.465 | -1.000 | 6 | -7.826 |
| brutto (ohne alle Kosten) | OOS | 58 | 0.459 | 1.792 | 0.431 | 1.844 | 26.638 | 2.328 | -0.956 | 7.092 | -1.000 | 6 | -5.892 |
| brutto (ohne alle Kosten) | gesamt | 178 | 0.590 | 3.758 | 0.449 | 2.123 | 105.103 | 2.484 | -0.955 | 7.465 | -1.000 | 6 | -7.826 |

## Kostenanteile (Ø je Trade, in R)

Spread+Kommission 0.031 R | Swap Tickmill 0.010 R | Swap TTP 0.061 R | Ø Haltedauer 8.7 Kalendertage

## Je Jahr (Swap TTP)

| einstieg | n | Ø R | Σ R |
|---|---|---|---|
| 2016 | 20 | 0.753 | 15.059 |
| 2017 | 15 | 1.064 | 15.961 |
| 2018 | 19 | 0.314 | 5.967 |
| 2019 | 18 | -0.042 | -0.750 |
| 2020 | 22 | 0.263 | 5.775 |
| 2021 | 26 | 0.912 | 23.724 |
| 2022 | 19 | 0.925 | 17.572 |
| 2023 | 21 | 0.198 | 4.157 |
| 2024 | 18 | 0.070 | 1.263 |

## Je Markt (Swap TTP)

| markt | n | Ø R | Σ R |
|---|---|---|---|
| AUDUSD | 16 | 1.439 | 23.019 |
| EURUSD | 25 | -0.029 | -0.737 |
| GBPUSD | 25 | 0.114 | 2.840 |
| NZDUSD | 27 | 0.618 | 16.694 |
| USDCAD | 12 | 0.539 | 6.467 |
| USDCHF | 12 | 1.306 | 15.667 |
| USDJPY | 20 | 0.310 | 6.200 |
| XAGUSD | 26 | 0.420 | 10.907 |
| XAUUSD | 15 | 0.512 | 7.673 |

## Je Richtung (Swap TTP)

| seite | n | Ø R | Σ R |
|---|---|---|---|
| long | 85 | 0.806 | 68.538 |
| short | 93 | 0.217 | 20.190 |

## Konto 100.000 $ ab 2016, Zinseszins, Swap TTP

| Risiko je Trade | Endkapital | CAGR | max. DD |
|---|---|---|---|
| 1% | 230974 | 0.098 | -0.082 |
| 2% | 485739 | 0.193 | -0.159 |
| 5% | 2776237 | 0.449 | -0.357 |
| 10% | 13159082 | 0.723 | -0.600 |

Max. gleichzeitig offene Trades: 4 → offenes Risiko bis 4× Risiko je Trade.
