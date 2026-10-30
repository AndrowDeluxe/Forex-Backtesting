# Residual Edge Analysis

**Status:** RESIDUAL_FRAGILE
**Decision eligibility:** REVIEW_REQUIRED
**Period:** 2024-07-01 to 2026-08-14 (535 observations)
**Primary model:** hold_Gold

## Primary Model

| Metric | Value |
|---|---:|
| R² | 0.0859 |
| Adjusted R² | 0.0842 |
| Annualized alpha | 23.4067% |
| Alpha HAC t-stat | 2.961 |
| Annualized residual volatility | 12.9610% |
| Residual edge ratio | 1.806 |

## Baseline Loadings

| Baseline | Loading | HAC t-stat | VIF |
|---|---:|---:|---:|
| base_return | 0.1689 | 5.587 | 1.000 |

## Model Sensitivity

| Model | Role | R² | Annualized alpha | Residual edge ratio | Status |
|---|---|---:|---:|---:|---|
| hold_Gold | primary | 0.0859 | 23.4067% | 1.806 | RESIDUAL_FRAGILE |
| gold_plus_silver | sensitivity | 0.0893 | 23.4672% | 1.814 | RESIDUAL_FRAGILE |

## Evidence Warnings

- **HIGH — RETURN_BASIS_MISMATCH:** Strategy and baseline returns use different gross/net cost bases.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model hold_Gold could not estimate 9 rolling windows.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model gold_plus_silver could not estimate 9 rolling windows.

## Regime Breakdown

### regime

| Regime | N | Evidence | Annualized active return | Active Sharpe |
|---|---:|---|---:|---:|
| g↑·accel × π↑·accel | 154 | ADEQUATE | 39.1301% | 2.496 |
| g↑·accel × π↑·slow | 96 | ADEQUATE | 20.8749% | 2.018 |
| g↑·slow × π↑·accel | 162 | ADEQUATE | 16.2866% | 1.236 |
| g↑·slow × π↑·slow | 123 | ADEQUATE | 15.0745% | 1.419 |

## Interpretation

- 9 rolling windows could not be estimated.
- This report does not authorize a trade or an automatic exposure change.
- Confirm exploratory findings on untouched out-of-sample or live data.
