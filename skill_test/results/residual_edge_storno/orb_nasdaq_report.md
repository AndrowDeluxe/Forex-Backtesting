# Residual Edge Analysis

**Status:** RESIDUAL_FRAGILE
**Decision eligibility:** REVIEW_REQUIRED
**Period:** 2023-01-03 to 2026-09-30 (939 observations)
**Primary model:** hold_NDX

## Primary Model

| Metric | Value |
|---|---:|
| R² | 0.0023 |
| Adjusted R² | 0.0012 |
| Annualized alpha | 23.4713% |
| Alpha HAC t-stat | 1.160 |
| Annualized residual volatility | 39.2274% |
| Residual edge ratio | 0.598 |

## Baseline Loadings

| Baseline | Loading | HAC t-stat | VIF |
|---|---:|---:|---:|
| base_return | 0.0930 | 0.712 | 1.000 |

## Model Sensitivity

| Model | Role | R² | Annualized alpha | Residual edge ratio | Status |
|---|---|---:|---:|---:|---|
| hold_NDX | primary | 0.0023 | 23.4713% | 0.598 | RESIDUAL_FRAGILE |
| base_plus_trend | sensitivity | 0.0027 | 23.2501% | 0.593 | RESIDUAL_FRAGILE |

## Evidence Warnings

- **HIGH — RETURN_BASIS_MISMATCH:** Strategy and baseline returns use different gross/net cost bases.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model base_plus_trend could not estimate 743 rolling windows.

## Regime Breakdown

### regime

| Regime | N | Evidence | Annualized active return | Active Sharpe |
|---|---:|---|---:|---:|
| g↑·accel × π↑·accel | 274 | ADEQUATE | 22.9590% | 0.501 |
| g↑·accel × π↑·slow | 243 | ADEQUATE | 30.1318% | 0.721 |
| g↑·slow × π↑·accel | 187 | ADEQUATE | 15.9358% | 0.470 |
| g↑·slow × π↑·slow | 235 | ADEQUATE | 23.1776% | 0.734 |

## Interpretation

- Residual evidence does not clear all robustness thresholds.
- This report does not authorize a trade or an automatic exposure change.
- Confirm exploratory findings on untouched out-of-sample or live data.
