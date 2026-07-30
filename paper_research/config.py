"""Tunable knobs for the paper-research pipeline. Edit this file to change
what gets searched for — no code changes needed elsewhere."""

# arXiv q-fin categories to search (see https://arxiv.org/archive/q-fin).
ARXIV_CATEGORIES = [
    "q-fin.TR",  # Trading and Market Microstructure
    "q-fin.ST",  # Statistical Finance
    "q-fin.PM",  # Portfolio Management
]

# Keywords ORed together across titles/abstracts. Keep specific enough to
# stay relevant to this repo's strategy universe (FX/futures/crypto
# intraday signals), not generic finance.
ARXIV_KEYWORDS = [
    "VWAP",
    "order flow",
    "volume profile",
    "mean reversion FX",
    "momentum futures",
    "market microstructure trading strategy",
    "intraday trading signal",
    # Mean-reversion / statistical arbitrage
    "pairs trading",
    "statistical arbitrage",
    "mean reversion equities",
    # Momentum / trend-following
    "trend following strategy",
    "momentum strategy",
    "breakout strategy",
    # Crypto-specific
    "cryptocurrency trading strategy",
    "bitcoin market microstructure",
]

ARXIV_MAX_RESULTS_PER_KEYWORD = 20

# Local drop-in folder for manually-sourced PDFs (SSRN, blogs, course PDFs,
# ...) -- see paper_dropbox/README.md. Gitignored except for that README, so
# the PDFs themselves never land in a commit.
PAPER_DROPBOX_DIR = "paper_dropbox"

PAPER_CACHE_DIR = "paper_cache"
STORE_DIR = "paper_research_cache"

# Cheap model for extraction -- structured-output task, not creative writing.
ANTHROPIC_EXTRACTION_MODEL = "claude-haiku-4-5"

# Cap on characters of paper text sent to the LLM per call (abstract +
# leading sections cover the strategy description in practice; keeps token
# cost bounded regardless of paper length).
MAX_EXTRACTION_CHARS = 12000
