# Residual Edge Analysis

**Status:** RESIDUAL_FRAGILE
**Decision eligibility:** REVIEW_REQUIRED
**Period:** 2024-08-01 to 2026-09-30 (545 observations)
**Primary model:** hold_Gold

## Primary Model

| Metric | Value |
|---|---:|
| R² | 0.0266 |
| Adjusted R² | 0.0248 |
| Annualized alpha | 32.2666% |
| Alpha HAC t-stat | 2.150 |
| Annualized residual volatility | 22.4614% |
| Residual edge ratio | 1.437 |

## Baseline Loadings

| Baseline | Loading | HAC t-stat | VIF |
|---|---:|---:|---:|
| base_return | 0.1567 | 2.878 | 1.000 |

## Model Sensitivity

| Model | Role | R² | Annualized alpha | Residual edge ratio | Status |
|---|---|---:|---:|---:|---|
| hold_Gold | primary | 0.0266 | 32.2666% | 1.437 | RESIDUAL_FRAGILE |
| gold_plus_silver | sensitivity | 0.0277 | 32.3189% | 1.440 | RESIDUAL_FRAGILE |

## Evidence Warnings

- **HIGH — RETURN_BASIS_MISMATCH:** Strategy and baseline returns use different gross/net cost bases.
- **HIGH — NOT_OUT_OF_SAMPLE:** Treat in-sample residual edge as exploratory until confirmed out of sample.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model hold_Gold could not estimate 42 rolling windows.
- **HIGH — ROLLING_ANALYSIS_INCOMPLETE:** Model gold_plus_silver could not estimate 42 rolling windows.

## Regime Breakdown

### regime

| Regime | N | Evidence | Annualized active return | Active Sharpe |
|---|---:|---|---:|---:|
| g↑·accel × π↑·accel | 154 | ADEQUATE | 36.5737% | 1.476 |
| g↑·accel × π↑·slow | 92 | ADEQUATE | 31.5578% | 1.307 |
| g↑·slow × π↑·accel | 175 | ADEQUATE | 14.9344% | 0.986 |
| g↑·slow × π↑·slow | 124 | ADEQUATE | 51.9040% | 1.950 |

## Interpretation

- 42 rolling windows could not be estimated.
- This report does not authorize a trade or an automatic exposure change.
- Confirm exploratory findings on untouched out-of-sample or live data.
