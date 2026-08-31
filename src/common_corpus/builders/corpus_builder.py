"""Phase B2 — materialize the Common Corpus (papers/paper_topics parquet + manifest).

Principles (spec §15, §20, §21): pinned upstream revision, deterministic output
(ORDER BY paper_id -> stable sha256), and no silent drops — every filter stage is counted.
"""
from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel

from common_corpus.config import PROJECT_ROOT, UpstreamConfig
from common_corpus.providers.science_lake import ScienceLakeClient

log = logging.getLogger("corpus_builder")
SQL_DIR = PROJECT_ROOT / "sql"


class ScopeConfig(BaseModel):
    field: str
    language: str | None = None
    require_valid_title_abstract: bool = True
    require_arxiv_id: bool = True
    exclude_retracted: bool = True
    exclude_paratext: bool = True


class CitationConfig(BaseModel):
    source: str = "openalex"
    snapshot_date: str = ""


class TemporalConfig(BaseModel):
    arxiv_snapshot_duckdb: str | None = None
    arxiv_snapshot_label: str | None = None


class CorpusConfig(BaseModel):
    corpus_version: str
    output_dir: str
    scope: ScopeConfig
    citation: CitationConfig
    temporal: TemporalConfig = TemporalConfig()

    @property
    def output_path(self) -> Path:
        p = Path(self.output_dir)
        return p if p.is_absolute() else PROJECT_ROOT / p


def load_corpus_config(path: str | Path | None = None) -> CorpusConfig:
    path = Path(path) if path else PROJECT_ROOT / "config" / "corpus.yaml"
    with open(path) as f:
        return CorpusConfig(**yaml.safe_load(f))


def _sql(name: str) -> str:
    return (SQL_DIR / name).read_text()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while blk := f.read(1 << 24):
            h.update(blk)
    return h.hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return None


def build(up: UpstreamConfig, cfg: CorpusConfig, sample: int | None = None, threads: int = 32) -> Path:
    out = cfg.output_path
    out.mkdir(parents=True, exist_ok=True)
    client = ScienceLakeClient(up, mode="local", threads=threads)
    con = client.con
    timings: dict[str, float] = {}
    audit: dict[str, int] = {}

    def step(name: str, fn):
        t0 = time.time()
        r = fn()
        timings[name] = round(time.time() - t0, 1)
        log.info("%s done in %.1fs", name, timings[name])
        return r

    # 1) CS pool
    step("build_pool", lambda: con.execute(_sql("build_cs_pool.sql"), {"field": cfg.scope.field}))
    if sample:
        con.execute(f"CREATE OR REPLACE TEMP TABLE pool AS SELECT * FROM pool ORDER BY work_id LIMIT {int(sample)}")
    audit["pool_works"] = con.sql("SELECT count(*) FROM pool").fetchone()[0]

    # 2) arXiv ids from location URLs
    step("extract_arxiv", lambda: con.execute(_sql("extract_arxiv_ids.sql")))
    audit["pool_with_arxiv_id"] = con.sql("SELECT count(*) FROM arxiv_map").fetchone()[0]
    audit["arxiv_id_conflicts"] = con.sql("SELECT count(*) FROM arxiv_map WHERE n_distinct_ids > 1").fetchone()[0]

    # 3) one scan of works -> candidates temp table, then cheap filter audit (no silent drops)
    s = cfg.scope
    step("build_candidates", lambda: con.execute(_sql("build_candidates.sql"), {
        "citation_snapshot": cfg.citation.snapshot_date, "source_snapshot": up.openalex_snapshot}))
    params = {
        "require_valid": s.require_valid_title_abstract,
        "language": s.language,
        "exclude_retracted": s.exclude_retracted,
        "exclude_paratext": s.exclude_paratext,
        "require_arxiv": s.require_arxiv_id,
    }
    # 3b) temporal resolution (D2): arXiv snapshot (day) -> id YYMM (month) -> openalex (day)
    tconf = cfg.temporal
    if tconf.arxiv_snapshot_duckdb and Path(tconf.arxiv_snapshot_duckdb).exists():
        con.execute(f"ATTACH '{tconf.arxiv_snapshot_duckdb}' AS arxiv_snapshot (READ_ONLY)")
        step("resolve_temporal", lambda: con.execute(_sql("resolve_temporal.sql")))
    else:
        log.warning("no arxiv snapshot source — falling back to id-month/openalex only")
        con.execute("CREATE OR REPLACE TEMP TABLE arxiv_snapshot_papers_missing AS SELECT 1")
        con.execute("""CREATE OR REPLACE TEMP TABLE arxiv_dates AS
            SELECT paper_id, CAST(NULL AS DATE) id_month, CAST(NULL AS DATE) snap_date FROM candidates WHERE FALSE""")

    def _count(overrides: dict) -> int:
        p = {**params, **overrides}
        return con.execute(f"SELECT count(*) FROM ({_sql('build_papers.sql')})", p).fetchone()[0]

    step("audit_filters", lambda: audit.update({
        "pool_rows_unfiltered": _count({"require_valid": False, "language": None, "exclude_retracted": False,
                                        "exclude_paratext": False, "require_arxiv": False}),
        "after_valid_title_abstract": _count({"language": None, "exclude_retracted": False,
                                              "exclude_paratext": False, "require_arxiv": False}),
        "after_language": _count({"exclude_retracted": False, "exclude_paratext": False, "require_arxiv": False}),
        "after_clean_flags": _count({"require_arxiv": False}),
    }))

    papers_path = out / "papers.parquet"
    step("write_papers", lambda: con.execute(
        f"COPY ({_sql('build_papers.sql')}) TO '{papers_path}' (FORMAT PARQUET, COMPRESSION ZSTD)", params))
    con.execute(f"CREATE OR REPLACE TEMP TABLE selected AS SELECT paper_id FROM '{papers_path}'")
    audit["papers_final"] = con.sql("SELECT count(*) FROM selected").fetchone()[0]
    pre_dedup = con.execute(
        f"SELECT count(*) FROM ({_sql('build_papers.sql').split('QUALIFY')[0]})", params
    ).fetchone()[0]
    audit["arxiv_dedup_dropped"] = pre_dedup - audit["papers_final"]

    # 4) paper_topics.parquet
    topics_path = out / "paper_topics.parquet"
    step("write_topics", lambda: con.execute(
        f"COPY ({_sql('build_topics.sql')}) TO '{topics_path}' (FORMAT PARQUET, COMPRESSION ZSTD)"))
    audit["paper_topics_rows"] = con.sql(f"SELECT count(*) FROM '{topics_path}'").fetchone()[0]

    # 5) temporal stats + violations (kept, not dropped — spec §18.2)
    tstats = {r[0] + "/" + r[1]: r[2] for r in con.sql(f"""
        SELECT date_source, date_precision, count(*) FROM '{papers_path}' GROUP BY 1,2 ORDER BY 3 DESC
    """).fetchall()}
    tviol = con.sql(f"""
        SELECT count(*) FROM '{papers_path}'
        WHERE first_public_date IS NOT NULL AND publication_date IS NOT NULL
          AND first_public_date > publication_date
    """).fetchone()[0]
    audit["first_public_gt_publication"] = tviol

    # 5b) coverage stats on the final set
    cov = con.sql(f"""
        SELECT count(*),
               count(doi), count(arxiv_id), count(abstract),
               count(publication_date), min(year), max(year)
        FROM '{papers_path}'
    """).fetchone()
    coverage = {
        "papers": cov[0], "doi": cov[1], "arxiv_id": cov[2], "abstract": cov[3],
        "publication_date": cov[4], "year_min": cov[5], "year_max": cov[6],
    }

    manifest = {
        "corpus_version": cfg.corpus_version,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sample": sample,
        "upstream": {"source": up.repo_id, "dataset_revision": up.revision, "openalex_snapshot": up.openalex_snapshot},
        "selection": cfg.scope.model_dump(),
        "citation": cfg.citation.model_dump(),
        "code_commit": _git_commit(),
        "temporal": {
            "arxiv_snapshot_source": tconf.arxiv_snapshot_duckdb,
            "arxiv_snapshot_label": tconf.arxiv_snapshot_label,
            "resolution": tstats,
        },
        "audit": audit,
        "coverage": coverage,
        "timings_seconds": timings,
        "paper_count": audit["papers_final"],
        "papers_sha256": _sha256(papers_path),
        "paper_topics_sha256": _sha256(topics_path),
        "papers_bytes": papers_path.stat().st_size,
        "paper_topics_bytes": topics_path.stat().st_size,
    }
    mpath = out / "manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2))
    log.info("manifest: %s", mpath)
    log.info("audit: %s", json.dumps(audit))
    return mpath
