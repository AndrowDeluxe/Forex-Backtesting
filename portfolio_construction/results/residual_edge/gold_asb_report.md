# Residual Edge Analysis

**Status:** RESIDUAL_FRAGILE
**Decision eligibility:** REVIEW_REQUIRED
**Period:** 2023-01-03 to 2026-09-30 (941 observations)
**Primary model:** hold_Gold

## Primary Model

| Metric | Value |
|---|---:|
| R² | 0.0090 |
| Adjusted R² | 0.0080 |
| Annualized alpha | 6.0392% |
| Alpha HAC t-stat | 2.423 |
| Annualized residual volatility | 4.9066% |
| Residual edge ratio | 1.231 |

## Baseline Loadings

| Baseline | Loading | HAC t-stat | VIF |
|---|---:|---:|---:|
| base_return | 0.0232 | 2.530 | 1.000 |

## Model Sensitivity

| Model | Role | R² | Annualized alpha | Residual edge ratio | Status |
|---|---|---:|---:|---:|---|
| hold_Gold | primary | 0.0090 | 6.0392% | 1.231 | RESIDUAL_EDGE |
| base_plus_trend | sensitivity | 0.0090 | 6.0445% | 1.232 | RESIDUAL_FRAGILE |
| gold_plus_silver | sensitivity | 0.0092 | 6.0502% | 1.233 | RESIDUAL_EDGE |

## Evidence Warnings

- **HIGH — RETURN_BASIS_MISMATCH:** Strategy and baseline returns use different gross/net cost bases.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model base_plus_trend could not estimate 820 rolling windows.
- **HIGH — MULTICOLLINEARITY:** Model base_plus_trend baseline base_return has VIF > 10 or is singular.
- **HIGH — MULTICOLLINEARITY:** Model base_plus_trend baseline trend_return has VIF > 10 or is singular.

## Regime Breakdown

### regime

| Regime | N | Evidence | Annualized active return | Active Sharpe |
|---|---:|---|---:|---:|
| g↑·accel × π↑·accel | 274 | ADEQUATE | 8.5303% | 1.933 |
| g↑·accel × π↑·slow | 243 | ADEQUATE | 3.0873% | 0.603 |
| g↑·slow × π↑·accel | 189 | ADEQUATE | 8.5659% | 1.522 |
| g↑·slow × π↑·slow | 235 | ADEQUATE | 4.1552% | 0.899 |

## Interpretation

- Alpha, residual edge ratio, and rolling stability clear the configured thresholds.
- Diagnostic status changes under alternate declared baselines.
- This report does not authorize a trade or an automatic exposure change.
- Confirm exploratory findings on untouched out-of-sample or live data.
