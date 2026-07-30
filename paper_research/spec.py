"""Shared data shapes for the paper-research pipeline.

`StrategySpec` is the LLM extraction's output contract: everything downstream
(`auto_backtest.py`, `combine.py`, the dashboard) reads only this shape, never
the paper's raw text directly, so the extraction step is the single place
that has to change if the schema evolves.
"""

from dataclasses import dataclass, field
from typing import Literal

Complexity = Literal["simple_signal", "stateful"]


@dataclass
class StructuredCondition:
    """A single indicator/threshold or crossover test, e.g. `adx < 25` or
    `close crosses_above vwap`. Only meaningful when the parent spec's
    complexity is "simple_signal" — see auto_backtest.py's interpreter for
    the exact grammar this must conform to.
    """

    indicator: str  # one of auto_backtest.SUPPORTED_INDICATORS
    op: Literal["<", "<=", ">", ">=", "crosses_above", "crosses_below"]
    value: str  # numeric string for threshold ops, indicator name (e.g. "vwap") for crosses_*


@dataclass
class StrategySpec:
    source: Literal["arxiv", "dropbox", "combo"]
    source_id: str  # arxiv id, or dropbox filename
    title: str
    asset_class: str
    timeframe: str
    indicators: list[str]
    entry_rule_text: str
    exit_rule_text: str
    risk_rule_text: str
    session_filter: str | None
    claimed_performance: str | None
    complexity: Complexity
    entry_conditions: list[StructuredCondition] = field(default_factory=list)
    direction: Literal["long", "short", "both"] = "both"
    notes: str = ""


@dataclass
class PaperRecord:
    """One row in the store: a processed paper plus whatever the pipeline
    could produce for it (spec always present once extracted; backtest
    metrics only for simple_signal specs that ran successfully)."""

    spec: StrategySpec
    backtest_metrics: dict | None = None
    backtest_error: str | None = None
