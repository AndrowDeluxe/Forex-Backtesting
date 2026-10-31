# Residual Edge Analysis

**Status:** RESIDUAL_FRAGILE
**Decision eligibility:** REVIEW_REQUIRED
**Period:** 2023-01-03 to 2026-09-30 (939 observations)
**Primary model:** hold_SPX

## Primary Model

| Metric | Value |
|---|---:|
| R² | 0.0072 |
| Adjusted R² | 0.0062 |
| Annualized alpha | 11.3287% |
| Alpha HAC t-stat | 1.241 |
| Annualized residual volatility | 18.8518% |
| Residual edge ratio | 0.601 |

## Baseline Loadings

| Baseline | Loading | HAC t-stat | VIF |
|---|---:|---:|---:|
| base_return | 0.1096 | 2.417 | 1.000 |

## Model Sensitivity

| Model | Role | R² | Annualized alpha | Residual edge ratio | Status |
|---|---|---:|---:|---:|---|
| hold_SPX | primary | 0.0072 | 11.3287% | 0.601 | RESIDUAL_FRAGILE |
| base_plus_trend | sensitivity | 0.0087 | 11.3210% | 0.601 | RESIDUAL_FRAGILE |

## Evidence Warnings

- **HIGH — RETURN_BASIS_MISMATCH:** Strategy and baseline returns use different gross/net cost bases.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model base_plus_trend could not estimate 743 rolling windows.

## Regime Breakdown

### regime

| Regime | N | Evidence | Annualized active return | Active Sharpe |
|---|---:|---|---:|---:|
| g↑·accel × π↑·accel | 274 | ADEQUATE | 25.7565% | 1.197 |
| g↑·accel × π↑·slow | 243 | ADEQUATE | 12.2241% | 0.663 |
| g↑·slow × π↑·accel | 187 | ADEQUATE | 17.1913% | 0.965 |
| g↑·slow × π↑·slow | 235 | ADEQUATE | -11.0845% | -0.666 |

## Interpretation

- Residual evidence does not clear all robustness thresholds.
- Rolling alpha is positive in too few windows.
- This report does not authorize a trade or an automatic exposure change.
- Confirm exploratory findings on untouched out-of-sample or live data.
