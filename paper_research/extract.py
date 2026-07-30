"""LLM-based extraction: raw paper text -> StrategySpec. Uses Claude Haiku
(cheap; structured-output task, not creative writing) via `output_config.format`
so the response is guaranteed-valid JSON matching the schema -- no tool-use
round trip needed for a single-shot extraction like this.
"""

import json

import anthropic

from paper_research import config
from paper_research.spec import StrategySpec, StructuredCondition

_SCHEMA = {
    "type": "object",
    "properties": {
        "asset_class": {"type": "string"},
        "timeframe": {"type": "string"},
        "indicators": {"type": "array", "items": {"type": "string"}},
        "entry_rule_text": {"type": "string"},
        "exit_rule_text": {"type": "string"},
        "risk_rule_text": {"type": "string"},
        "session_filter": {"type": "string"},
        "claimed_performance": {"type": "string"},
        "complexity": {"type": "string", "enum": ["simple_signal", "stateful"]},
        "direction": {"type": "string", "enum": ["long", "short", "both"]},
        "entry_conditions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "indicator": {"type": "string"},
                    "op": {
                        "type": "string",
                        "enum": ["<", "<=", ">", ">=", "crosses_above", "crosses_below"],
                    },
                    "value": {"type": "string"},
                },
                "required": ["indicator", "op", "value"],
                "additionalProperties": False,
            },
        },
        "notes": {"type": "string"},
    },
    "required": [
        "asset_class", "timeframe", "indicators", "entry_rule_text",
        "exit_rule_text", "risk_rule_text", "session_filter",
        "claimed_performance", "complexity", "direction", "entry_conditions", "notes",
    ],
    "additionalProperties": False,
}

_SYSTEM_PROMPT = """You extract trading-strategy rules from academic/practitioner \
finance papers into a strict structured format. Be literal and conservative:

- Only extract rules the paper actually states; don't infer parameters it \
doesn't give.
- Classify complexity as "simple_signal" ONLY if the whole strategy reduces to \
a single-bar indicator threshold or crossover check (e.g. "enter when RSI < 30", \
"enter when price crosses above its 20-period MA"). If the strategy needs \
multi-bar state (tracking an evolving leg/range, waiting for a later \
confirmation bar, session-dependent multi-phase logic, or anything that can't \
be evaluated from one bar's indicator values alone), classify it as "stateful" \
- when in doubt, choose "stateful" over "simple_signal", since a wrong \
"simple_signal" label would cause an automated backtest to misrepresent the \
paper's actual strategy.
- entry_conditions should only be populated for "simple_signal" strategies; \
leave it as an empty list for "stateful" ones.
- If the paper reports backtest results, summarize them verbatim/faithfully in \
claimed_performance (don't editorialize) or leave it as an empty string if none \
are reported.
- Use an empty string "" for any field with no applicable information."""


def extract_spec(
    source: str,
    source_id: str,
    title: str,
    text: str,
    client: anthropic.Anthropic | None = None,
) -> StrategySpec:
    client = client or anthropic.Anthropic()
    truncated = text[: config.MAX_EXTRACTION_CHARS]

    response = client.messages.create(
        model=config.ANTHROPIC_EXTRACTION_MODEL,
        max_tokens=2000,
        system=_SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": f"Paper title: {title}\n\nPaper text (may be truncated):\n{truncated}",
            }
        ],
    )
    text_block = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text_block)

    conditions = [StructuredCondition(**c) for c in data.pop("entry_conditions")]
    return StrategySpec(
        source=source,
        source_id=source_id,
        title=title,
        entry_conditions=conditions,
        **data,
    )
