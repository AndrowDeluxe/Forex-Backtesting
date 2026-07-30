"""Orchestrates the paper-research pipeline: arXiv search (+ local dropbox) ->
PDF ingest -> Claude extraction -> auto-backtest (simple_signal specs only) ->
store. Run manually (`python scripts/research_paper_pipeline.py`), like the
other scripts/research_*.py studies in this repo -- NOT invoked from the
Streamlit app, so viewing the dashboard never needs ANTHROPIC_API_KEY.

Requires ANTHROPIC_API_KEY set in the environment before running (extraction
step calls the Anthropic API). Without it, every candidate will fail at the
extraction step -- printed and skipped, not a crash.
"""

import traceback

from paper_research import arxiv_search, combine, config, extract, pdf_ingest, store
from paper_research.auto_backtest import UnsupportedSpecError, run_auto_backtest
from paper_research.spec import PaperRecord
from strategy.metrics import summarize
from strategy.real_data import fetch_pair_history

# Generic proxy instrument/window for auto-backtesting simple_signal specs --
# deliberately NOT trying to match each paper's own stated asset class (most
# papers don't name a FX pair anyway); this is a screening pass, not a
# faithful replication of each paper's own data.
DEFAULT_PAIR = "EURUSD"
DEFAULT_START, DEFAULT_END = "2016-01-01", "2026-01-01"


def _backtest_data():
    return fetch_pair_history(DEFAULT_PAIR, DEFAULT_START, DEFAULT_END)


def process_candidate(source: str, source_id: str, title: str, text: str, backtest_df) -> None:
    if store.has_record(source_id):
        print(f"  skip (already processed): {source_id}")
        return

    try:
        spec = extract.extract_spec(source=source, source_id=source_id, title=title, text=text)
    except Exception:
        print(f"  extraction FAILED for {source_id}:")
        traceback.print_exc()
        return

    record = PaperRecord(spec=spec)
    if spec.complexity == "simple_signal":
        try:
            trades = run_auto_backtest(backtest_df, spec)
            record.backtest_metrics = (
                summarize(trades, backtest_df.index) if not trades.empty else {"n_trades": 0}
            )
        except UnsupportedSpecError as exc:
            record.backtest_error = str(exc)
    else:
        record.backtest_error = "stateful complexity -- needs manual reconstruction"

    store.save_record(record)
    print(f"  saved: {source_id} ({spec.complexity}) -- {title[:70]}")


def run() -> None:
    print(f"Searching arXiv ({len(config.ARXIV_KEYWORDS)} keywords)...")
    candidates = arxiv_search.search_all_keywords()
    print(f"Found {len(candidates)} unique arXiv candidates.")

    backtest_df = _backtest_data()

    for c in candidates:
        if store.has_record(c.arxiv_id):
            continue
        print(f"Processing arxiv:{c.arxiv_id} - {c.title[:70]}")
        try:
            text = pdf_ingest.fetch_arxiv_text(c)
        except Exception:
            print(f"  PDF fetch FAILED for {c.arxiv_id}:")
            traceback.print_exc()
            continue
        process_candidate("arxiv", c.arxiv_id, c.title, text, backtest_df)

    dropbox_pdfs = pdf_ingest.list_dropbox_pdfs()
    print(f"Found {len(dropbox_pdfs)} PDFs in {config.PAPER_DROPBOX_DIR}/")
    for path in dropbox_pdfs:
        source_id = path.stem
        if store.has_record(source_id):
            continue
        print(f"Processing dropbox:{source_id}")
        text = pdf_ingest.read_dropbox_text(path)
        process_candidate("dropbox", source_id, source_id, text, backtest_df)

    print("Stage 2: generating cross-paper combination candidates...")
    all_records = [r for r in store.load_all_records() if r.spec.source != "combo"]
    combo_candidates = [
        c for c in combine.suggest_combinations(all_records) if not store.has_record(c.source_id)
    ]
    print(f"  {len(combo_candidates)} new combination candidate(s).")
    for combo_record in combine.backtest_combinations(combo_candidates, backtest_df):
        store.save_record(combo_record)
        print(f"  saved: {combo_record.spec.source_id}")


if __name__ == "__main__":
    run()
