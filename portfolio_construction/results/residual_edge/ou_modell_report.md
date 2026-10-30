# Residual Edge Analysis

**Status:** RESIDUAL_FRAGILE
**Decision eligibility:** REVIEW_REQUIRED
**Period:** 2023-01-03 to 2026-09-09 (924 observations)
**Primary model:** hold_SPX

## Primary Model

| Metric | Value |
|---|---:|
| R² | 0.0184 |
| Adjusted R² | 0.0173 |
| Annualized alpha | 0.6524% |
| Alpha HAC t-stat | 0.375 |
| Annualized residual volatility | 2.9064% |
| Residual edge ratio | 0.224 |

## Baseline Loadings

| Baseline | Loading | HAC t-stat | VIF |
|---|---:|---:|---:|
| base_return | 0.0270 | 3.864 | 1.000 |

## Model Sensitivity

| Model | Role | R² | Annualized alpha | Residual edge ratio | Status |
|---|---|---:|---:|---:|---|
| hold_SPX | primary | 0.0184 | 0.6524% | 0.224 | RESIDUAL_FRAGILE |
| base_plus_trend | sensitivity | 0.0185 | 0.6519% | 0.224 | RESIDUAL_FRAGILE |

## Evidence Warnings

- **HIGH — RETURN_BASIS_MISMATCH:** Strategy and baseline returns use different gross/net cost bases.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model base_plus_trend could not estimate 728 rolling windows.

## Regime Breakdown

### regime

| Regime | N | Evidence | Annualized active return | Active Sharpe |
|---|---:|---|---:|---:|
| g↑·accel × π↑·accel | 274 | ADEQUATE | -2.7797% | -0.950 |
| g↑·accel × π↑·slow | 243 | ADEQUATE | 4.8199% | 1.873 |
| g↑·slow × π↑·accel | 174 | ADEQUATE | 1.7023% | 0.492 |
| g↑·slow × π↑·slow | 233 | ADEQUATE | -0.4422% | -0.161 |

## Interpretation

- Residual evidence does not clear all robustness thresholds.
- Rolling alpha is positive in too few windows.
- This report does not authorize a trade or an automatic exposure change.
- Confirm exploratory findings on untouched out-of-sample or live data.
