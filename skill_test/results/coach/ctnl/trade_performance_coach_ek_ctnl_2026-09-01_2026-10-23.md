# Trade Performance Coach Report: ek_ctnl_2026-09-01_2026-10-23

**Verdict:** `COOL_DOWN`
**Review type:** `monthly_aggregate`
**Primary root cause:** `risk_sizing`

## Scores

- `process_score`: 100
- `risk_score`: 10
- `execution_score`: 85
- `review_quality_score`: 88

## Process Adherence

- **INFO** `pre_entry_thesis_record` — met: A pre-entry thesis record is present

## Risk Manager Notes

- **CRITICAL** `position_size` — Actual risk materially exceeded the planned or maximum risk. Evidence: actual.risk_r=46.99, reference_r=1
- **CRITICAL** `portfolio_heat` — Portfolio heat exceeded the provided maximum. Evidence: portfolio_heat_r=140.97, max_portfolio_heat_r=2
- **CRITICAL** `drawdown` — Consecutive losses are elevated; consider temporary review-only mode. Evidence: monthly.consecutive_losses=12

## Execution Quality

- **INFO** `entry` — No explicit early-entry issue was detected from the provided record. Evidence: actual.entry_before_confirmation is false or absent
- **WARNING** `stop` — Stop was moved after entry. Evidence: actual.stop_moved is true

## Possible Behavioral Patterns

- `size_creep` (high): Actual risk exceeded the planned or maximum risk (actual.risk_r=46.99 > reference_r=1).
  - Reflection: What would this trade have looked like at the planned risk size?

## Next-Session Operating Rules

- **next_two_trades**: Cap risk at 0.5R for the next two trades unless the trader explicitly modifies the risk plan in the journal.
  - Trigger: size_creep tag
  - Reason: Actual risk exceeded the stated risk plan.
- **next_session**: Switch to review-only mode for the next session; do not add new risk until the rule review is journaled.
  - Trigger: possible revenge/cool-down condition
  - Reason: Repeated losses or revenge-trade evidence can escalate risk-taking.

## Coach Questions

- What would this trade have looked like at the planned risk size?

## Human Decision Gate

Do you accept these temporary operating rules, modify them, defer the decision, or journal this review only?

Allowed actions: accept_rules, modify_rules, defer, journal_only
Default action: `journal_only`

## Disclaimer

This review is for trading-process improvement only. It is not financial advice, investment advice, therapy, mental-health diagnosis, or a trading signal. The human trader remains responsible for all decisions and risk.
