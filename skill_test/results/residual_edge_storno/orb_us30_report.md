# Residual Edge Analysis

**Status:** RESIDUAL_FRAGILE
**Decision eligibility:** REVIEW_REQUIRED
**Period:** 2023-01-03 to 2026-09-30 (939 observations)
**Primary model:** hold_DJI

## Primary Model

| Metric | Value |
|---|---:|
| R² | 0.0011 |
| Adjusted R² | -0.0000 |
| Annualized alpha | -0.1904% |
| Alpha HAC t-stat | -0.026 |
| Annualized residual volatility | 14.1822% |
| Residual edge ratio | -0.013 |

## Baseline Loadings

| Baseline | Loading | HAC t-stat | VIF |
|---|---:|---:|---:|
| base_return | 0.0345 | 0.927 | 1.000 |

## Model Sensitivity

| Model | Role | R² | Annualized alpha | Residual edge ratio | Status |
|---|---|---:|---:|---:|---|
| hold_DJI | primary | 0.0011 | -0.1904% | -0.013 | RESIDUAL_FRAGILE |
| base_plus_trend | sensitivity | 0.0011 | -0.1777% | -0.013 | RESIDUAL_FRAGILE |

## Evidence Warnings

- **HIGH — RETURN_BASIS_MISMATCH:** Strategy and baseline returns use different gross/net cost bases.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model base_plus_trend could not estimate 726 rolling windows.

## Regime Breakdown

### regime

| Regime | N | Evidence | Annualized active return | Active Sharpe |
|---|---:|---|---:|---:|
| g↑·accel × π↑·accel | 274 | ADEQUATE | -23.7579% | -1.854 |
| g↑·accel × π↑·slow | 243 | ADEQUATE | 13.1991% | 0.932 |
| g↑·slow × π↑·accel | 187 | ADEQUATE | 15.3586% | 0.905 |
| g↑·slow × π↑·slow | 235 | ADEQUATE | 1.0698% | 0.081 |

## Interpretation

- Residual evidence does not clear all robustness thresholds.
- Rolling alpha is positive in too few windows.
- This report does not authorize a trade or an automatic exposure change.
- Confirm exploratory findings on untouched out-of-sample or live data.
