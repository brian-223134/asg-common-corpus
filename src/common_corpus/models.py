"""PaperRecord v0.1 — canonical schema (spec §6) + ID normalization.

The canonical corpus stores metadata only; full text is resolved lazily (spec §2.2).
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, field_validator

# --- ID normalization ---------------------------------------------------------

_DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:")

# new-style 2403.12345 / old-style cs/0301012, math.GT/0309136 — optional version suffix
_ARXIV_ID = r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Za-z]{2})?/\d{7})"
ARXIV_ID_RE = re.compile(rf"({_ARXIV_ID})(v\d+)?", re.IGNORECASE)
ARXIV_URL_RE = re.compile(rf"arxiv\.org/(?:abs|pdf)/({_ARXIV_ID})(v\d+)?", re.IGNORECASE)


def normalize_doi(doi: str | None) -> str | None:
    """Lowercase, prefix-free DOI (Science Data Lake xref convention)."""
    if not doi:
        return None
    d = doi.strip().lower()
    for p in _DOI_PREFIXES:
        if d.startswith(p):
            d = d[len(p):]
            break
    return d or None


def normalize_openalex_id(oid: str | None) -> str | None:
    """'https://openalex.org/W123' | 'w123' -> 'W123'."""
    if not oid:
        return None
    s = oid.strip().rsplit("/", 1)[-1].upper()
    if not re.fullmatch(r"W\d+", s):
        raise ValueError(f"invalid OpenAlex work id: {oid!r}")
    return s


def normalize_arxiv_id(aid: str | None) -> str | None:
    """Base arXiv id (version stripped, archive lowercased) — cross-corpus join key."""
    if not aid:
        return None
    m = ARXIV_ID_RE.fullmatch(aid.strip())
    if not m:
        return None
    base = m.group(1)
    if "/" in base:  # old-style: lowercase the archive part, keep e.g. math.GT casing? -> lower all
        base = base.lower()
    return base


def arxiv_id_from_url(url: str | None) -> str | None:
    if not url:
        return None
    m = ARXIV_URL_RE.search(url)
    return normalize_arxiv_id(m.group(1) + (m.group(2) or "")) if m else None


# --- Schema -------------------------------------------------------------------

class DatePrecision(str, Enum):
    day = "day"
    month = "month"
    year = "year"
    unknown = "unknown"


class PaperRecord(BaseModel):
    # identity
    paper_id: str                      # canonical: OpenAlex short id (W...)
    openalex_id: str
    doi: str | None = None
    arxiv_id: str | None = None
    version_family_id: str | None = None
    # content
    title: str
    abstract: str
    language: str | None = None
    # temporal
    first_public_date: date | None = None
    publication_date: date | None = None
    date_source: str = "unresolved"
    date_precision: DatePrecision = DatePrecision.unknown
    # bibliographic
    authors: list[str] = []
    venue: str | None = None
    paper_type: str | None = None
    year: int | None = None
    # impact
    citation_count: int | None = None
    citation_source: str = "openalex"
    citation_snapshot_date: date | None = None
    # provenance
    metadata_source: str = "openalex"
    source_snapshot: str | None = None
    record_created_at: datetime | None = None
    record_hash: str | None = None
    # fulltext locator
    fulltext_available_hint: bool | None = None

    @field_validator("doi")
    @classmethod
    def _doi(cls, v):
        return normalize_doi(v)

    @field_validator("openalex_id", "paper_id")
    @classmethod
    def _oa(cls, v):
        return normalize_openalex_id(v)

    @field_validator("arxiv_id")
    @classmethod
    def _ax(cls, v):
        if v is None:
            return None
        n = normalize_arxiv_id(v)
        if n is None:
            raise ValueError(f"invalid arXiv id: {v!r}")
        return n

    @field_validator("citation_count")
    @classmethod
    def _cc(cls, v):
        if v is not None and v < 0:
            raise ValueError("negative citation_count")
        return v

    def compute_hash(self) -> str:
        """Deterministic content hash over identity+content+temporal+impact fields."""
        payload = {
            "paper_id": self.paper_id, "openalex_id": self.openalex_id, "doi": self.doi,
            "arxiv_id": self.arxiv_id, "title": self.title, "abstract": self.abstract,
            "language": self.language,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "first_public_date": self.first_public_date.isoformat() if self.first_public_date else None,
            "paper_type": self.paper_type, "year": self.year,
            "citation_count": self.citation_count, "source_snapshot": self.source_snapshot,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
