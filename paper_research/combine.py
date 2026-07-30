"""Stage 2: cross-paper combination suggestions.

Only combines the structured `entry_conditions` of "simple_signal" specs --
"stateful" specs were never reduced to structured atoms in the first place
(see spec.py's docstring), so there is nothing combinable to extract from
them automatically. This is a scope limitation, not an oversight: combining a
stateful strategy's rules would need a much richer extraction schema than
this project currently has.

Combinations that are themselves simple_signal-compatible (which all
generated combinations are, by construction) can be run straight through
`auto_backtest.run_auto_backtest` unmodified.
"""

from itertools import combinations as _combinations

import pandas as pd

from paper_research.auto_backtest import UnsupportedSpecError, run_auto_backtest
from paper_research.spec import PaperRecord, StrategySpec
from strategy.metrics import summarize


def suggest_combinations(records: list[PaperRecord]) -> list[StrategySpec]:
    """Pairs one entry condition from each of two DIFFERENT papers, requiring
    the same trade direction (combining opposite-direction signals with a
    simple AND is nonsensical) and different indicators (combining two
    conditions on the same indicator is redundant, not a real combination).
    """
    simple = [r for r in records if r.spec.complexity == "simple_signal" and r.spec.entry_conditions]

    candidates = []
    for rec_a, rec_b in _combinations(simple, 2):
        if rec_a.spec.source_id == rec_b.spec.source_id:
            continue
        if rec_a.spec.direction == "both" or rec_a.spec.direction != rec_b.spec.direction:
            continue

        for cond_a in rec_a.spec.entry_conditions:
            for cond_b in rec_b.spec.entry_conditions:
                if cond_a.indicator == cond_b.indicator:
                    continue
                combo_id = (
                    f"combo__{rec_a.spec.source_id}__{rec_b.spec.source_id}"
                    f"__{cond_a.indicator}_{cond_b.indicator}"
                )
                candidates.append(
                    StrategySpec(
                        source="combo",
                        source_id=combo_id,
                        title=f"Kombination: {rec_a.spec.title[:40]} x {rec_b.spec.title[:40]}",
                        asset_class="n/a (Kombination)",
                        timeframe="n/a (Kombination)",
                        indicators=sorted({cond_a.indicator, cond_b.indicator}),
                        entry_rule_text=(
                            f"({cond_a.indicator} {cond_a.op} {cond_a.value}) AND "
                            f"({cond_b.indicator} {cond_b.op} {cond_b.value})"
                        ),
                        exit_rule_text="generischer ATR-Stop/Target (wie Einzel-Paper-Auto-Backtest)",
                        risk_rule_text="n/a",
                        session_filter=None,
                        claimed_performance=None,
                        complexity="simple_signal",
                        entry_conditions=[cond_a, cond_b],
                        direction=rec_a.spec.direction,
                        notes=f"Kombiniert Bausteine aus {rec_a.spec.source_id} und {rec_b.spec.source_id}.",
                    )
                )
    return candidates


def backtest_combinations(
    candidates: list[StrategySpec], backtest_df: pd.DataFrame
) -> list[PaperRecord]:
    """Runs every candidate through the generic auto-backtest engine. A
    candidate that turns out unsupported (e.g. an indicator combination the
    engine can't evaluate) is recorded with `backtest_error` set, same
    honesty convention as single-paper specs -- never silently dropped."""
    results = []
    for spec in candidates:
        record = PaperRecord(spec=spec)
        try:
            trades = run_auto_backtest(backtest_df, spec)
            record.backtest_metrics = summarize(trades, backtest_df.index) if not trades.empty else {"n_trades": 0}
        except UnsupportedSpecError as exc:
            record.backtest_error = str(exc)
        results.append(record)
    return results
