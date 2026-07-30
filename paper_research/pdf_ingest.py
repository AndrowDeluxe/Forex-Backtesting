"""PDF -> plain text, source-agnostic. Takes either an arXiv candidate (from
arxiv_search.py, downloaded over HTTP) or a local file path (the
paper_dropbox/ folder -- e.g. manually-sourced SSRN PDFs, since SSRN has no
public search/download API and scraping its search pages would violate its
terms of use). Both paths land in the same PAPER_CACHE_DIR text cache keyed
by source_id, so a paper is only ever downloaded/parsed once.
"""

from pathlib import Path

import requests
from pypdf import PdfReader

from paper_research import config
from paper_research.arxiv_search import ArxivCandidate


def _cache_path(source_id: str) -> Path:
    safe_id = source_id.replace("/", "_")
    return Path(config.PAPER_CACHE_DIR) / f"{safe_id}.txt"


def _extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def fetch_arxiv_text(candidate: ArxivCandidate, timeout: float = 30.0) -> str:
    cache_path = _cache_path(candidate.arxiv_id)
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    resp = requests.get(candidate.pdf_url, timeout=timeout)
    resp.raise_for_status()

    tmp_pdf = cache_path.with_suffix(".pdf")
    tmp_pdf.parent.mkdir(parents=True, exist_ok=True)
    tmp_pdf.write_bytes(resp.content)
    try:
        text = _extract_text(tmp_pdf)
    finally:
        tmp_pdf.unlink(missing_ok=True)

    cache_path.write_text(text, encoding="utf-8")
    return text


def list_dropbox_pdfs() -> list[Path]:
    dropbox = Path(config.PAPER_DROPBOX_DIR)
    if not dropbox.exists():
        return []
    return sorted(dropbox.glob("*.pdf"))


def read_dropbox_text(pdf_path: Path) -> str:
    source_id = pdf_path.stem
    cache_path = _cache_path(source_id)
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    text = _extract_text(pdf_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")
    return text
