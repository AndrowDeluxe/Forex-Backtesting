# Residual Edge Analysis

**Status:** RESIDUAL_FRAGILE
**Decision eligibility:** REVIEW_REQUIRED
**Period:** 2022-06-01 to 2026-09-30 (1356 observations)
**Primary model:** hold_EURUSD

## Primary Model

| Metric | Value |
|---|---:|
| R² | 0.0019 |
| Adjusted R² | 0.0012 |
| Annualized alpha | 4.9435% |
| Alpha HAC t-stat | 1.909 |
| Annualized residual volatility | 6.1252% |
| Residual edge ratio | 0.807 |

## Baseline Loadings

| Baseline | Loading | HAC t-stat | VIF |
|---|---:|---:|---:|
| base_return | 0.0389 | 1.271 | 1.000 |

## Model Sensitivity

| Model | Role | R² | Annualized alpha | Residual edge ratio | Status |
|---|---|---:|---:|---:|---|
| hold_EURUSD | primary | 0.0019 | 4.9435% | 0.807 | RESIDUAL_FRAGILE |
| base_plus_trend | sensitivity | 0.0046 | 5.0530% | 0.826 | RESIDUAL_FRAGILE |

## Evidence Warnings

- **HIGH — RETURN_BASIS_MISMATCH:** Strategy and baseline returns use different gross/net cost bases.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model hold_EURUSD could not estimate 38 rolling windows.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model base_plus_trend could not estimate 609 rolling windows.

## Regime Breakdown

### regime

| Regime | N | Evidence | Annualized active return | Active Sharpe |
|---|---:|---|---:|---:|
| g↑·accel × π↑·accel | 342 | ADEQUATE | 11.1807% | 1.806 |
| g↑·accel × π↑·slow | 331 | ADEQUATE | -6.7980% | -1.651 |
| g↑·slow × π↑·accel | 283 | ADEQUATE | 3.9343% | 0.634 |
| g↑·slow × π↑·slow | 400 | ADEQUATE | 10.0408% | 1.383 |

## Interpretation

- 38 rolling windows could not be estimated.
- This report does not authorize a trade or an automatic exposure change.
- Confirm exploratory findings on untouched out-of-sample or live data.
