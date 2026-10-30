# Trade Hypothesis Report

## Summary
Top hypothesis: CTNL-H1 (Skip CTNL reversals when growth and inflation both accelerate) with priority score 3.8.

## State Assessment
Ranked hypotheses validated against guardrails.

## Hypotheses
### CTNL-H1: Skip CTNL reversals when growth and inflation both accelerate
- Recommendation: pursue
- Priority Score: 3.8
- Thesis: Gold reversal setups fail when growth and inflation accelerate together because gold trends persist in reflation phases.
- Mechanism: Reflation drives persistent real-asset demand; failed-continuation signals are overrun by trend flow, so reversal stops get hit.
- Expected Impact: Removes ~28 % of trades, little R

### CTNL-H2: Avoid Friday entries (weekend hold)
- Recommendation: pursue
- Priority Score: 3.4
- Thesis: Reversal entries on Friday carry weekend gap risk inside a 96h hold.
- Mechanism: Weekend gaps jump past the 3-ATR stop and remove the time the reversal needs; Monday reopen often resumes the trend.
- Expected Impact: Removes ~17 % of trades

### CTNL-H3: Trade CTNL only in high-VIX tercile
- Recommendation: park
- Priority Score: 3.1
- Thesis: Reversals work better when cross-asset fear is high.
- Mechanism: High VIX means forced deleveraging, gold sold for liquidity then reverses.
- Expected Impact: Removes ~66 % of trades

### CTNL-H4: Skip July
- Recommendation: reject
- Priority Score: 2.35
- Thesis: July weak.
- Mechanism: Calendar only.
- Expected Impact: Removes ~16 % of trades

## Risks
- 30 trades only
- overlaps with existing ribbon/regime kill-switch
- 18 trades only
- keeps only 36 IS trades
- both other terciles also positive
- calendar mining

## Next Actions
- Run MVE: IS comparison filtered vs unfiltered, counted as one trial
- Run MVE: IS comparison filtered vs unfiltered, counted as one trial
