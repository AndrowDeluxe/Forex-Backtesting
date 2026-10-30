# Trade Performance Coach Report: ek_orb_2026-09-01_2026-10-23

**Verdict:** `COOL_DOWN`
**Review type:** `monthly_aggregate`
**Primary root cause:** `risk_sizing`

## Scores

- `process_score`: 100
- `risk_score`: 70
- `execution_score`: 100
- `review_quality_score`: 88

## Process Adherence

- **INFO** `pre_entry_thesis_record` — met: A pre-entry thesis record is present

## Risk Manager Notes

- **INFO** `position_size` — Actual risk was within the provided risk limit. Evidence: actual.risk_r=0.5, reference_r=1
- **CRITICAL** `drawdown` — Consecutive losses are elevated; consider temporary review-only mode. Evidence: monthly.consecutive_losses=10

## Execution Quality

- **INFO** `entry` — No explicit early-entry issue was detected from the provided record. Evidence: actual.entry_before_confirmation is false or absent

## Possible Behavioral Patterns

- `no_pattern_detected` (low): No behavior pattern was detected from the available evidence.
  - Reflection: Is there any additional journal context that should be added before finalizing this review?

## Next-Session Operating Rules

- **next_session**: Switch to review-only mode for the next session; do not add new risk until the rule review is journaled.
  - Trigger: possible revenge/cool-down condition
  - Reason: Repeated losses or revenge-trade evidence can escalate risk-taking.

## Coach Questions

- Is there any additional journal context that should be added before finalizing this review?

## Human Decision Gate

Do you accept these temporary operating rules, modify them, defer the decision, or journal this review only?

Allowed actions: accept_rules, modify_rules, defer, journal_only
Default action: `journal_only`

## Disclaimer

This review is for trading-process improvement only. It is not financial advice, investment advice, therapy, mental-health diagnosis, or a trading signal. The human trader remains responsible for all decisions and risk.
