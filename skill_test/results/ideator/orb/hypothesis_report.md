# Trade Hypothesis Report

## Summary
Top hypothesis: ORB-H1 (Trade ORB only after a negative 20-day index return) with priority score 4.2.

## State Assessment
Ranked hypotheses validated against guardrails.

## Hypotheses
### ORB-H1: Trade ORB only after a negative 20-day index return
- Recommendation: pursue
- Priority Score: 4.2
- Thesis: Opening-range breakouts follow through more often after the index has fallen over the prior 20 days.
- Mechanism: After declines realised volatility and dealer short-gamma rise, so intraday moves extend instead of mean-reverting; in grinding uptrends the open range is noise.
- Expected Impact: Fewer trades (~40 %), higher avg R

### ORB-H2: Skip ORB in growth-slowing x inflation-accelerating regime
- Recommendation: park
- Priority Score: 3.4
- Thesis: ORB expectancy collapses when growth slows while inflation accelerates (stagflation tilt).
- Mechanism: Rate-shock driven sessions reverse after the open as macro headlines dominate intraday flow.
- Expected Impact: Removes ~20 % of trades

### ORB-H3: Skip ORB in mid-VIX tercile
- Recommendation: reject
- Priority Score: 2.7
- Thesis: Mid volatility days have neither trend persistence nor large ranges.
- Mechanism: None convincing; non-monotone pattern suggests noise.
- Expected Impact: Removes ~33 % of trades

### ORB-H4: Skip ORB in February and July
- Recommendation: reject
- Priority Score: 2.35
- Thesis: Seasonal weak months.
- Mechanism: None beyond calendar coincidence.
- Expected Impact: Removes ~16 % of trades

## Risks
- drops 60 % of trades incl. big winners
- 2019-2022 IS contains 2020 crash and 2022 bear market, overrepresenting declines
- regime labels are monthly macro data, slow and revised (first prints used)
- mechanism loose
- tercile bounds are IS-fitted
- non-monotone = likely noise
- pure calendar mining over 4 IS years

## Next Actions
- Run MVE: IS comparison filtered vs unfiltered, counted as one trial
