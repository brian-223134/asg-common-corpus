"""Phase B4 — CorpusView: cutoff + GT exclusion over a built corpus (spec §8.4).

A view is NOT a physical copy of the corpus: it materializes only the surviving
paper_id list plus a manifest chaining back to the base corpus hash. Agents (or
the survey-search integration) join `paper_ids.parquet` against the base
`papers.parquet`, or use `materialize()` to export a filtered papers.parquet
when a standalone file is more convenient.

Cutoff semantics (docs/decisions.md D2 follow-up):
- precision=day  -> include iff first_public_date <= cutoff
- precision=month (date stored at month START) -> under the default `strict`
  policy include iff the month END <= cutoff, because a month-start date makes a
  paper look EARLIER than reality; comparing the month start against the cutoff
  would leak papers that actually appeared after it. `lenient` compares the
  stored month-start date instead (documented, for sensitivity analysis only).
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from pydantic import BaseModel

from common_corpus.config import PROJECT_ROOT

log = logging.getLogger("corpus_view")


class ViewConfig(BaseModel):
    name: str
    cutoff: str                                  # ISO date, inclusive
    month_precision_policy: str = "strict"       # strict | lenient
    exclude_arxiv_ids: list[str] = []
    exclude_paper_ids: list[str] = []


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while blk := f.read(1 << 24):
            h.update(blk)
    return h.hexdigest()


CUTOFF_PREDICATE = {
    "strict": """
        (date_precision = 'day' AND first_public_date <= CAST($cutoff AS DATE))
        OR (date_precision = 'month'
            AND last_day(first_public_date) <= CAST($cutoff AS DATE))
    """,
    "lenient": "first_public_date <= CAST($cutoff AS DATE)",
}


def create_view(corpus_dir: Path, cfg: ViewConfig, out_root: Path | None = None,
                materialize: bool = False) -> Path:
    corpus_dir = Path(corpus_dir)
    papers = corpus_dir / "papers.parquet"
    base_manifest = json.loads((corpus_dir / "manifest.json").read_text())
    out = (out_root or PROJECT_ROOT / "data" / "views") / cfg.name
    out.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("CREATE TEMP TABLE ex_arxiv (id VARCHAR)")
    if cfg.exclude_arxiv_ids:
        con.executemany("INSERT INTO ex_arxiv VALUES (?)", [(i,) for i in cfg.exclude_arxiv_ids])
    con.execute("CREATE TEMP TABLE ex_paper (id VARCHAR)")
    if cfg.exclude_paper_ids:
        con.executemany("INSERT INTO ex_paper VALUES (?)", [(i,) for i in cfg.exclude_paper_ids])

    pred = CUTOFF_PREDICATE[cfg.month_precision_policy]
    counts = {}
    counts["base_papers"] = con.sql(f"SELECT count(*) FROM '{papers}'").fetchone()[0]
    counts["pass_cutoff"] = con.execute(
        f"SELECT count(*) FROM '{papers}' WHERE ({pred})", {"cutoff": cfg.cutoff}).fetchone()[0]
    counts["excluded_by_arxiv_id"] = con.execute(f"""
        SELECT count(*) FROM '{papers}' WHERE ({pred})
          AND arxiv_id IN (SELECT id FROM ex_arxiv)""", {"cutoff": cfg.cutoff}).fetchone()[0]
    counts["excluded_by_paper_id"] = con.execute(f"""
        SELECT count(*) FROM '{papers}' WHERE ({pred})
          AND arxiv_id NOT IN (SELECT id FROM ex_arxiv)
          AND paper_id IN (SELECT id FROM ex_paper)""", {"cutoff": cfg.cutoff}).fetchone()[0]

    ids_path = out / "paper_ids.parquet"
    con.execute(f"""
        COPY (
            SELECT paper_id, arxiv_id FROM '{papers}'
            WHERE ({pred})
              AND arxiv_id NOT IN (SELECT id FROM ex_arxiv)
              AND paper_id NOT IN (SELECT id FROM ex_paper)
            ORDER BY paper_id
        ) TO '{ids_path}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """, {"cutoff": cfg.cutoff})
    counts["view_papers"] = con.sql(f"SELECT count(*) FROM '{ids_path}'").fetchone()[0]

    # sanity: nothing past cutoff, no excluded id survives (spec §17 B4 acceptance)
    viol = con.execute(f"""
        SELECT count(*) FROM '{papers}' p JOIN '{ids_path}' v USING (paper_id)
        WHERE NOT ({pred}) OR p.arxiv_id IN (SELECT id FROM ex_arxiv)
           OR p.paper_id IN (SELECT id FROM ex_paper)
    """, {"cutoff": cfg.cutoff}).fetchone()[0]
    if viol:
        raise RuntimeError(f"view invariant violated for {viol} rows")

    files = {"paper_ids.parquet": _sha256(ids_path)}
    if materialize:
        mat = out / "papers.parquet"
        con.execute(f"""
            COPY (SELECT p.* FROM '{papers}' p JOIN '{ids_path}' v USING (paper_id)
                  ORDER BY p.paper_id)
            TO '{mat}' (FORMAT PARQUET, COMPRESSION ZSTD)""")
        files["papers.parquet"] = _sha256(mat)

    manifest = {
        "view_name": cfg.name,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": cfg.model_dump(),
        "base_corpus": {
            "path": str(corpus_dir),
            "corpus_version": base_manifest["corpus_version"],
            "papers_sha256": base_manifest["papers_sha256"],
            "dataset_revision": base_manifest["upstream"]["dataset_revision"],
        },
        "counts": counts,
        "files_sha256": files,
    }
    mpath = out / "view_manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2))
    log.info("view %s: %s", cfg.name, json.dumps(counts))
    return mpath
