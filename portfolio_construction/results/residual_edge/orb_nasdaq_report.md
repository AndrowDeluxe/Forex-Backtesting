# Residual Edge Analysis

**Status:** RESIDUAL_FRAGILE
**Decision eligibility:** REVIEW_REQUIRED
**Period:** 2023-01-03 to 2026-09-30 (939 observations)
**Primary model:** hold_NDX

## Primary Model

| Metric | Value |
|---|---:|
| R² | 0.0001 |
| Adjusted R² | -0.0009 |
| Annualized alpha | 29.3813% |
| Alpha HAC t-stat | 1.088 |
| Annualized residual volatility | 54.5096% |
| Residual edge ratio | 0.539 |

## Baseline Loadings

| Baseline | Loading | HAC t-stat | VIF |
|---|---:|---:|---:|
| base_return | -0.0313 | -0.207 | 1.000 |

## Model Sensitivity

| Model | Role | R² | Annualized alpha | Residual edge ratio | Status |
|---|---|---:|---:|---:|---|
| hold_NDX | primary | 0.0001 | 29.3813% | 0.539 | RESIDUAL_FRAGILE |
| base_plus_trend | sensitivity | 0.0019 | 28.7179% | 0.527 | RESIDUAL_FRAGILE |

## Evidence Warnings

- **HIGH — RETURN_BASIS_MISMATCH:** Strategy and baseline returns use different gross/net cost bases.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model base_plus_trend could not estimate 743 rolling windows.

## Regime Breakdown

### regime

| Regime | N | Evidence | Annualized active return | Active Sharpe |
|---|---:|---|---:|---:|
| g↑·accel × π↑·accel | 274 | ADEQUATE | 35.9531% | 0.596 |
| g↑·accel × π↑·slow | 243 | ADEQUATE | 22.4056% | 0.405 |
| g↑·slow × π↑·accel | 187 | ADEQUATE | 63.7837% | 1.120 |
| g↑·slow × π↑·slow | 235 | ADEQUATE | 1.5566% | 0.036 |

## Interpretation

- Residual evidence does not clear all robustness thresholds.
- Rolling alpha is positive in too few windows.
- This report does not authorize a trade or an automatic exposure change.
- Confirm exploratory findings on untouched out-of-sample or live data.
