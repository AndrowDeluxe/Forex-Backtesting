"""Free, keyless search against the public arXiv API
(https://info.arxiv.org/help/api/user-manual.html) restricted to the q-fin
categories in config.py. Returns metadata only -- pdf_ingest.py does the
actual download.
"""

from dataclasses import dataclass
from xml.etree import ElementTree
from urllib.parse import quote

import requests

from paper_research import config

ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_API_URL = "http://export.arxiv.org/api/query"


@dataclass
class ArxivCandidate:
    arxiv_id: str  # e.g. "2401.01234v1"
    title: str
    abstract: str
    pdf_url: str
    published: str  # ISO 8601 string as returned by arXiv


def _build_query(keyword: str, categories: list[str]) -> str:
    cat_clause = " OR ".join(f"cat:{c}" for c in categories)
    kw_clause = f'(ti:"{keyword}" OR abs:"{keyword}")'
    return f"({kw_clause}) AND ({cat_clause})"


def search_keyword(keyword: str, max_results: int | None = None, timeout: float = 20.0) -> list[ArxivCandidate]:
    """One keyword, all configured categories. Raises on network errors --
    caller decides whether to skip or abort the whole run."""
    max_results = max_results or config.ARXIV_MAX_RESULTS_PER_KEYWORD
    query = _build_query(keyword, config.ARXIV_CATEGORIES)
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    resp = requests.get(ARXIV_API_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    return _parse_feed(resp.text)


def _parse_feed(xml_text: str) -> list[ArxivCandidate]:
    root = ElementTree.fromstring(xml_text)
    out = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        raw_id = entry.findtext(f"{ATOM_NS}id", default="")
        arxiv_id = raw_id.rsplit("/abs/", 1)[-1] if "/abs/" in raw_id else raw_id
        title = (entry.findtext(f"{ATOM_NS}title", default="") or "").strip().replace("\n", " ")
        abstract = (entry.findtext(f"{ATOM_NS}summary", default="") or "").strip().replace("\n", " ")
        published = entry.findtext(f"{ATOM_NS}published", default="") or ""
        pdf_url = ""
        for link in entry.findall(f"{ATOM_NS}link"):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")
                break
        if not pdf_url and arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        out.append(ArxivCandidate(arxiv_id=arxiv_id, title=title, abstract=abstract, pdf_url=pdf_url, published=published))
    return out


def search_all_keywords(keywords: list[str] | None = None) -> list[ArxivCandidate]:
    """Runs every configured keyword, de-duplicates by arxiv_id (many
    keywords will hit the same paper)."""
    keywords = keywords or config.ARXIV_KEYWORDS
    seen: dict[str, ArxivCandidate] = {}
    for kw in keywords:
        for candidate in search_keyword(kw):
            seen.setdefault(candidate.arxiv_id, candidate)
    return list(seen.values())
