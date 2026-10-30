# Residual Edge Analysis

**Status:** RESIDUAL_FRAGILE
**Decision eligibility:** REVIEW_REQUIRED
**Period:** 2023-01-03 to 2026-09-30 (941 observations)
**Primary model:** hold_Gold

## Primary Model

| Metric | Value |
|---|---:|
| R² | 0.0633 |
| Adjusted R² | 0.0623 |
| Annualized alpha | 9.4912% |
| Alpha HAC t-stat | 2.590 |
| Annualized residual volatility | 7.5298% |
| Residual edge ratio | 1.260 |

## Baseline Loadings

| Baseline | Loading | HAC t-stat | VIF |
|---|---:|---:|---:|
| base_return | 0.0969 | 5.299 | 1.000 |

## Model Sensitivity

| Model | Role | R² | Annualized alpha | Residual edge ratio | Status |
|---|---|---:|---:|---:|---|
| hold_Gold | primary | 0.0633 | 9.4912% | 1.260 | RESIDUAL_FRAGILE |
| base_plus_trend | sensitivity | 0.0648 | 9.2949% | 1.235 | RESIDUAL_FRAGILE |
| gold_plus_silver | sensitivity | 0.0662 | 9.4238% | 1.253 | RESIDUAL_FRAGILE |

## Evidence Warnings

- **HIGH — RETURN_BASIS_MISMATCH:** Strategy and baseline returns use different gross/net cost bases.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model hold_Gold could not estimate 16 rolling windows.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model base_plus_trend could not estimate 820 rolling windows.
- **HIGH — MULTICOLLINEARITY:** Model base_plus_trend baseline base_return has VIF > 10 or is singular.
- **HIGH — MULTICOLLINEARITY:** Model base_plus_trend baseline trend_return has VIF > 10 or is singular.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model gold_plus_silver could not estimate 16 rolling windows.

## Regime Breakdown

### regime

| Regime | N | Evidence | Annualized active return | Active Sharpe |
|---|---:|---|---:|---:|
| g↑·accel × π↑·accel | 274 | ADEQUATE | 11.5218% | 1.673 |
| g↑·accel × π↑·slow | 243 | ADEQUATE | 4.1967% | 0.624 |
| g↑·slow × π↑·accel | 189 | ADEQUATE | 12.2540% | 1.736 |
| g↑·slow × π↑·slow | 235 | ADEQUATE | 10.3764% | 1.122 |

## Interpretation

- 16 rolling windows could not be estimated.
- This report does not authorize a trade or an automatic exposure change.
- Confirm exploratory findings on untouched out-of-sample or live data.
