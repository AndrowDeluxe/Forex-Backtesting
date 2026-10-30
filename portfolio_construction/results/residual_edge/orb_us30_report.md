# Residual Edge Analysis

**Status:** RESIDUAL_FRAGILE
**Decision eligibility:** REVIEW_REQUIRED
**Period:** 2023-01-03 to 2026-09-30 (939 observations)
**Primary model:** hold_DJI

## Primary Model

| Metric | Value |
|---|---:|
| R² | 0.0010 |
| Adjusted R² | -0.0000 |
| Annualized alpha | -0.2270% |
| Alpha HAC t-stat | -0.031 |
| Annualized residual volatility | 14.1821% |
| Residual edge ratio | -0.016 |

## Baseline Loadings

| Baseline | Loading | HAC t-stat | VIF |
|---|---:|---:|---:|
| base_return | 0.0344 | 0.926 | 1.000 |

## Model Sensitivity

| Model | Role | R² | Annualized alpha | Residual edge ratio | Status |
|---|---|---:|---:|---:|---|
| hold_DJI | primary | 0.0010 | -0.2270% | -0.016 | RESIDUAL_FRAGILE |
| base_plus_trend | sensitivity | 0.0011 | -0.2143% | -0.015 | RESIDUAL_FRAGILE |

## Evidence Warnings

- **HIGH — RETURN_BASIS_MISMATCH:** Strategy and baseline returns use different gross/net cost bases.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model base_plus_trend could not estimate 726 rolling windows.

## Regime Breakdown

### regime

| Regime | N | Evidence | Annualized active return | Active Sharpe |
|---|---:|---|---:|---:|
| g↑·accel × π↑·accel | 274 | ADEQUATE | -23.7957% | -1.856 |
| g↑·accel × π↑·slow | 243 | ADEQUATE | 13.1641% | 0.930 |
| g↑·slow × π↑·accel | 187 | ADEQUATE | 15.3206% | 0.903 |
| g↑·slow × π↑·slow | 235 | ADEQUATE | 1.0341% | 0.078 |

## Interpretation

- Residual evidence does not clear all robustness thresholds.
- Rolling alpha is positive in too few windows.
- This report does not authorize a trade or an automatic exposure change.
- Confirm exploratory findings on untouched out-of-sample or live data.
