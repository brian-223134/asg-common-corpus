from __future__ import annotations

import logging
import time
from pathlib import Path

import typer

from common_corpus.config import load_upstream
from common_corpus.logging_utils import setup_logging

app = typer.Typer(help="Common Corpus for ASG agents.")
log = logging.getLogger("cli")


@app.command()
def doctor(config: Path = typer.Option(None, help="config/upstream.yaml")):
    """Check remote connectivity to the pinned Science Data Lake revision and the local mirror state."""
    from common_corpus.providers.science_lake import ScienceLakeClient

    setup_logging("doctor")
    cfg = load_upstream(config)
    t = time.time()
    c = ScienceLakeClient(cfg, mode="remote")
    n = c.query("SELECT count(*) FROM openalex.topics WHERE field_display_name='Computer Science'").fetchone()[0]
    log.info("remote ok: %d CS topics at %s (%.1fs)", n, cfg.revision[:7], time.time() - t)
    m = cfg.mirror_path / "upstream_manifest.json"
    if m.exists():
        import json
        mf = json.loads(m.read_text())
        done = [f for f, r in mf["files"].items() if r.get("verified")]
        log.info("mirror: %d/%d files verified at %s", len(done), len(cfg.files), cfg.mirror_path)
    else:
        log.info("mirror: not started (%s)", cfg.mirror_path)


@app.command()
def build(
    config: Path = typer.Option(None, help="config/corpus.yaml"),
    upstream_config: Path = typer.Option(None, help="config/upstream.yaml"),
    sample: int = typer.Option(None, help="limit the pool to N works (smoke test)"),
    threads: int = typer.Option(32),
):
    """Phase B2 — materialize papers.parquet / paper_topics.parquet / manifest.json from the local mirror."""
    from common_corpus.builders.corpus_builder import build as _build, load_corpus_config
    path = setup_logging("build")
    log.info("log file: %s", path)
    _build(load_upstream(upstream_config), load_corpus_config(config), sample=sample, threads=threads)


@app.command("create-view")
def create_view(
    name: str = typer.Option(..., help="view 이름 (config/benchmark_policy.yaml views.<name> 또는 옵션 직접 지정)"),
    corpus_dir: Path = typer.Option(Path("data/corpus/v0.1-poc")),
    cutoff: str = typer.Option(None, help="ISO date (config에 정의돼 있으면 생략 가능)"),
    exclude_arxiv: list[str] = typer.Option([], help="제외할 GT arXiv base id (반복 지정)"),
    exclude_file: Path = typer.Option(None, help="한 줄당 arXiv base id 하나인 파일"),
    month_policy: str = typer.Option(None, help="strict|lenient"),
    materialize: bool = typer.Option(False, help="필터된 papers.parquet도 함께 산출"),
):
    """Phase B4 — cutoff + GT exclusion을 적용한 CorpusView 생성."""
    import yaml
    from common_corpus.config import PROJECT_ROOT
    from common_corpus.corpus.view import ViewConfig, create_view as _create

    setup_logging("create_view")
    policy_file = PROJECT_ROOT / "config" / "benchmark_policy.yaml"
    base = {}
    if policy_file.exists():
        base = (yaml.safe_load(policy_file.read_text()).get("views") or {}).get(name, {})
    excl = list(base.get("exclude_arxiv_ids", [])) + list(exclude_arxiv)
    if exclude_file:
        excl += [l.strip() for l in exclude_file.read_text().splitlines() if l.strip()]
    cfg = ViewConfig(
        name=name,
        cutoff=cutoff or base.get("cutoff"),
        month_precision_policy=month_policy or base.get("month_precision_policy", "strict"),
        exclude_arxiv_ids=sorted(set(excl)),
        exclude_paper_ids=list(base.get("exclude_paper_ids", [])),
    )
    _create(corpus_dir if corpus_dir.is_absolute() else PROJECT_ROOT / corpus_dir, cfg, materialize=materialize)


@app.command()
def mirror(config: Path = typer.Option(None), no_verify: bool = typer.Option(False)):
    """Phase B0.5 — download the selective upstream mirror (resumable)."""
    from common_corpus.builders.mirror import mirror as _mirror

    path = setup_logging("mirror")
    log.info("log file: %s", path)
    cfg = load_upstream(config)
    _mirror(cfg, verify_existing=not no_verify)


if __name__ == "__main__":
    app()
