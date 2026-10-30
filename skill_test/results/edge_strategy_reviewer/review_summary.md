# Strategy Draft Review Summary

**Generated:** 2026-10-28T20:36:35+00:00
**Source:** C:\Users\andre\Forex-Backtesting\skill_test\drafts
**Drafts reviewed:** 2

## Verdict Summary

| Verdict | Count |
|---------|-------|
| PASS | 0 |
| REVISE | 2 |
| REJECT | 0 |
| Export Eligible | 0 |

## Individual Reviews

### ctnl_reversal_live_2026 — REVISE (confidence: 80)

| Criterion | Score | Severity | Reason |
|-----------|-------|----------|--------|
| C1_edge_plausibility | 95 | pass | Thesis contains specific causal reasoning. |
| C2_overfitting_risk | 80 | pass | 5 filters within acceptable range. |
| C3_sample_adequacy | 83 | pass | Estimated 87 annual opportunities. |
| C4_regime_dependency | 80 | pass | Strategy not restricted to single regime. |
| C5_exit_calibration | 80 | pass | Exit parameters acceptable (stop=1%, RR=5.0). |
| C6_risk_concentration | 80 | pass | Risk parameters within acceptable range. |
| C7_execution_realism | 50 | warn | No volume filter in entry conditions. |
| C8_invalidation_quality | 80 | pass | 3 invalidation signals defined. |

**Bias Checklist:**

| Item | Required | Addressed | Note |
|------|----------|-----------|------|
| look_ahead | True | False | Lake-H4-Duplikate: _bar_length 1 h statt 4 h, Soll/Sim sahen 3 h voraus; fruehere Risikohalbierung war Lookahead |
| survivorship | True | True | einzelnes Instrument XAUUSD |
| universe_selection | True | False | Gold gewaehlt, nachdem 6 FX-Paare und Continuation negativ waren -- Auswahl nach Ergebnis |
| delisted_securities | True | True | nicht anwendbar |
| earnings_announcement_timing | True | True | nicht anwendbar |
| split_dividend_adjustment | True | True | nicht anwendbar |
| transaction_costs_slippage | True | True | TTP-Kosten modelliert; 8 bps waren 4-11x zu hoch angesetzt |
| short_borrow_availability | True | True | CFD |
| liquidity_capacity | True | True | Gold-CFD, kleine Groessen |
| parameter_multiplicity | True | False | keine research_lock-Sperre, Versuche nie gezaehlt |
| walk_forward_out_of_sample | True | False | IS/OOS-Split lag komplett in 08/2024-08/2026; Walk-Forward 2016-2024 negativ |
| benchmark_attribution | True | True | Residual-Check 28.10.2026: t 2,15 (nur IS), 12 % Gold-Beta-Anteil |
| regime_dependence | True | True | Regime-Filter ist einziger Hebel; Edge nur long (short Summe -122 R) |

_Unaddressed required items: look_ahead, universe_selection, parameter_multiplicity, walk_forward_out_of_sample_

**Revision Instructions:**
- Declare how look_ahead, universe_selection, parameter_multiplicity, walk_forward_out_of_sample are addressed in the draft's bias_checklist block

### orb_live_2026 — REVISE (confidence: 83)

| Criterion | Score | Severity | Reason |
|-----------|-------|----------|--------|
| C1_edge_plausibility | 95 | pass | Thesis contains specific causal reasoning. |
| C2_overfitting_risk | 90 | pass | 4 filters within acceptable range. |
| C3_sample_adequacy | 86 | pass | Estimated 109 annual opportunities. |
| C4_regime_dependency | 80 | pass | Strategy not restricted to single regime. |
| C5_exit_calibration | 80 | pass | Exit parameters acceptable (stop=0%, RR=8.0). |
| C6_risk_concentration | 80 | pass | Risk parameters within acceptable range. |
| C7_execution_realism | 50 | warn | No volume filter in entry conditions. |
| C8_invalidation_quality | 80 | pass | 3 invalidation signals defined. |

**Bias Checklist:**

| Item | Required | Addressed | Note |
|------|----------|-----------|------|
| look_ahead | True | False | Fill-Bar-Stop wurde im Backtest nicht geprueft, Ein- und Ausstieg auf demselben Balken; 58-65 % der Entries in der ersten M5-Bar (Memory orb_first_bar, backtest_prueft_ein_und_ausstieg) |
| survivorship | True | True | Index-CFDs, kein Einzeltitel-Universum |
| universe_selection | True | False | Instrument- und Konfigurationsauswahl ab Stage 2 auf OOS-Zahlen (Anlass der Overfitting-Sperre); US30 nach OOS pausiert, NASDAQ-Storno als 2026-Fit |
| delisted_securities | True | True | nicht anwendbar |
| earnings_announcement_timing | True | True | nicht anwendbar fuer Index-CFDs |
| split_dividend_adjustment | True | True | Intraday, flat zum Close; Dividendenanpassung der CFDs irrelevant |
| transaction_costs_slippage | True | True | gemessene TTP/IQ/Tickmill-Kosten in der Simulation; Entry-Lag separat untersucht |
| short_borrow_availability | True | True | CFD, kein Leihbedarf |
| liquidity_capacity | True | True | Positionsgroessen weit unter Markttiefe der Indizes |
| parameter_multiplicity | True | True | 7.560 gezaehlte Versuche in ny_open_orb_is_reopt_7p, DSR ~0 |
| walk_forward_out_of_sample | True | True | IS-only-Reopt: Tresor PF 0,52 -- durchgefallen |
| benchmark_attribution | True | True | Residual-Check 28.10.2026: t 1,1-1,2, R2 < 0,01 |
| regime_dependence | True | True | Ribbon-Filter kippt 2026 (neutral schlug Trend 16/18 Jahre, im Tresor umgekehrt) |

_Unaddressed required items: look_ahead, universe_selection_

**Revision Instructions:**
- Declare how look_ahead, universe_selection are addressed in the draft's bias_checklist block

