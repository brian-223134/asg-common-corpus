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
def mirror(config: Path = typer.Option(None), no_verify: bool = typer.Option(False)):
    """Phase B0.5 — download the selective upstream mirror (resumable)."""
    from common_corpus.builders.mirror import mirror as _mirror

    path = setup_logging("mirror")
    log.info("log file: %s", path)
    cfg = load_upstream(config)
    _mirror(cfg, verify_existing=not no_verify)


if __name__ == "__main__":
    app()
