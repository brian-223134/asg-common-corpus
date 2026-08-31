import json
from datetime import date
from pathlib import Path

import duckdb
import pytest

from common_corpus.corpus.view import ViewConfig, create_view


@pytest.fixture()
def corpus(tmp_path: Path) -> Path:
    con = duckdb.connect()
    con.execute("""
        CREATE TABLE p AS SELECT * FROM (VALUES
            ('W1', '2401.00001', DATE '2024-01-15', 'day'),
            ('W2', '2403.00002', DATE '2024-03-01', 'month'),   -- 3월 어딘가 → strict면 cutoff 3/15 제외
            ('W3', '2402.00003', DATE '2024-02-01', 'month'),
            ('W4', '2405.00004', DATE '2024-05-02', 'day'),     -- cutoff 이후
            ('W5', 'cs/0301012', DATE '2003-01-20', 'day')      -- GT로 제외 예정
        ) t(paper_id, arxiv_id, first_public_date, date_precision)
    """)
    con.execute(f"COPY p TO '{tmp_path}/papers.parquet' (FORMAT PARQUET)")
    (tmp_path / "manifest.json").write_text(json.dumps({
        "corpus_version": "test", "papers_sha256": "x",
        "upstream": {"dataset_revision": "rev"}}))
    return tmp_path


def _ids(out_root: Path, name: str) -> set[str]:
    return {r[0] for r in duckdb.sql(f"SELECT paper_id FROM '{out_root}/{name}/paper_ids.parquet'").fetchall()}


def test_strict_month_cutoff_and_exclusion(corpus, tmp_path):
    cfg = ViewConfig(name="v1", cutoff="2024-03-15", exclude_arxiv_ids=["cs/0301012"])
    m = create_view(corpus, cfg, out_root=tmp_path / "views")
    assert _ids(tmp_path / "views", "v1") == {"W1", "W3"}  # W2: month-end 3/31 > 3/15, W4: 이후, W5: 제외
    mf = json.loads(m.read_text())
    assert mf["counts"]["excluded_by_arxiv_id"] == 1
    assert mf["counts"]["view_papers"] == 2


def test_lenient_month_cutoff(corpus, tmp_path):
    cfg = ViewConfig(name="v2", cutoff="2024-03-15", month_precision_policy="lenient")
    create_view(corpus, cfg, out_root=tmp_path / "views")
    assert "W2" in _ids(tmp_path / "views", "v2")  # 월초 비교라 포함 (감도분석용)


def test_deterministic(corpus, tmp_path):
    cfg = ViewConfig(name="v3", cutoff="2024-12-31")
    m1 = json.loads(create_view(corpus, cfg, out_root=tmp_path / "a").read_text())
    m2 = json.loads(create_view(corpus, cfg, out_root=tmp_path / "b").read_text())
    assert m1["files_sha256"] == m2["files_sha256"]


def test_materialize(corpus, tmp_path):
    cfg = ViewConfig(name="v4", cutoff="2024-12-31")
    create_view(corpus, cfg, out_root=tmp_path / "views", materialize=True)
    n = duckdb.sql(f"SELECT count(*) FROM '{tmp_path}/views/v4/papers.parquet'").fetchone()[0]
    assert n == 5  # cutoff 2024-12-31, 제외 없음 → 전부 포함
