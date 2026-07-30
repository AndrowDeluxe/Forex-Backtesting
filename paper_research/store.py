"""JSON persistence for processed papers, one file per source_id under
STORE_DIR (gitignored, like data_cache/). Existence of a record is also the
"already processed" check the pipeline uses to skip re-extraction (and
re-spending Anthropic API budget) on repeat runs.
"""

import json
from dataclasses import asdict
from pathlib import Path

from paper_research import config
from paper_research.spec import PaperRecord, StrategySpec, StructuredCondition


def _record_path(source_id: str) -> Path:
    safe_id = source_id.replace("/", "_")
    return Path(config.STORE_DIR) / f"{safe_id}.json"


def has_record(source_id: str) -> bool:
    return _record_path(source_id).exists()


def save_record(record: PaperRecord) -> None:
    path = _record_path(record.spec.source_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(record), indent=2, default=str), encoding="utf-8")


def _spec_from_dict(d: dict) -> StrategySpec:
    conditions = [StructuredCondition(**c) for c in d.get("entry_conditions", [])]
    return StrategySpec(**{**d, "entry_conditions": conditions})


def load_record(source_id: str) -> PaperRecord | None:
    path = _record_path(source_id)
    if not path.exists():
        return None
    d = json.loads(path.read_text(encoding="utf-8"))
    return PaperRecord(
        spec=_spec_from_dict(d["spec"]),
        backtest_metrics=d.get("backtest_metrics"),
        backtest_error=d.get("backtest_error"),
    )


def load_all_records() -> list[PaperRecord]:
    store_dir = Path(config.STORE_DIR)
    if not store_dir.exists():
        return []
    records = []
    for path in sorted(store_dir.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        records.append(
            PaperRecord(
                spec=_spec_from_dict(d["spec"]),
                backtest_metrics=d.get("backtest_metrics"),
                backtest_error=d.get("backtest_error"),
            )
        )
    return records
