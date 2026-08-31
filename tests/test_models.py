from datetime import date

import pytest

from common_corpus.models import (
    PaperRecord, arxiv_id_from_url, normalize_arxiv_id, normalize_doi, normalize_openalex_id,
)


def test_normalize_doi():
    assert normalize_doi("https://doi.org/10.1038/Nature12373") == "10.1038/nature12373"
    assert normalize_doi("doi:10.1/A B") == "10.1/a b"
    assert normalize_doi("10.5555/x") == "10.5555/x"
    assert normalize_doi(None) is None
    assert normalize_doi("") is None


def test_normalize_openalex_id():
    assert normalize_openalex_id("https://openalex.org/W2100837269") == "W2100837269"
    assert normalize_openalex_id("w42") == "W42"
    with pytest.raises(ValueError):
        normalize_openalex_id("A123")


def test_normalize_arxiv_id():
    assert normalize_arxiv_id("2403.12345v2") == "2403.12345"
    assert normalize_arxiv_id("2403.12345") == "2403.12345"
    assert normalize_arxiv_id("cs/0301012") == "cs/0301012"
    assert normalize_arxiv_id("math.GT/0309136v1") == "math.gt/0309136"
    assert normalize_arxiv_id("not-an-id") is None


def test_arxiv_id_from_url():
    assert arxiv_id_from_url("http://arxiv.org/abs/1811.06122v1") == "1811.06122"
    assert arxiv_id_from_url("https://arxiv.org/pdf/2101.00001") == "2101.00001"
    assert arxiv_id_from_url("http://arxiv.org/abs/cs/0301012") == "cs/0301012"
    assert arxiv_id_from_url("https://example.com/x.pdf") is None


def test_paper_record_roundtrip_and_hash():
    r = PaperRecord(
        paper_id="https://openalex.org/W1", openalex_id="W1",
        doi="https://doi.org/10.1/X", arxiv_id="2403.12345v3",
        title="T", abstract="A" * 60, language="en",
        publication_date=date(2024, 1, 2), year=2024,
        citation_count=3, source_snapshot="2026-02-03",
    )
    assert r.paper_id == "W1" and r.doi == "10.1/x" and r.arxiv_id == "2403.12345"
    h1 = r.compute_hash()
    assert h1 == r.model_copy().compute_hash()
    assert h1 != r.model_copy(update={"citation_count": 4}).compute_hash()


def test_paper_record_rejects_bad_values():
    with pytest.raises(Exception):
        PaperRecord(paper_id="W1", openalex_id="W1", title="t", abstract="a", citation_count=-1)
    with pytest.raises(Exception):
        PaperRecord(paper_id="W1", openalex_id="W1", title="t", abstract="a", arxiv_id="???")
