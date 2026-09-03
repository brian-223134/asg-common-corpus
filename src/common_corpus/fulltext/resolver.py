"""FullTextResolver (spec §8.5): cache-first lazy full text with version/hash freeze (§9).

Once a paper's text is cached it is never re-fetched: benchmark runs must reuse
the frozen version. Fetch/parse failures are recorded in the cache dir too, so
repeated runs don't silently retry forever (spec §21).
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from common_corpus.config import PROJECT_ROOT
from common_corpus.fulltext.parser import PARSER_VERSION, parse_eprint
from common_corpus.fulltext.providers import ArxivFullTextProvider, is_transient

log = logging.getLogger("fulltext.resolver")


@dataclass(frozen=True)
class FullTextDocument:
    paper_id: str | None
    source: str
    source_id: str
    version: str
    text: str
    fetched_at: str
    parser_version: str
    source_format: str
    sha256: str


class FullTextResolver:
    def __init__(self, corpus_dir: Path | None = None, cache_dir: Path | None = None,
                 provider: ArxivFullTextProvider | None = None):
        self.corpus_dir = Path(corpus_dir) if corpus_dir else PROJECT_ROOT / "data" / "corpus" / "v0.1-poc"
        self.cache_dir = Path(cache_dir) if cache_dir else PROJECT_ROOT / "data" / "fulltext_cache"
        self.provider = provider or ArxivFullTextProvider()

    def _arxiv_id_of(self, paper_id: str) -> str:
        r = duckdb.sql(f"SELECT arxiv_id FROM '{self.corpus_dir}/papers.parquet' WHERE paper_id = '{paper_id}'").fetchone()
        if not r or not r[0]:
            raise LookupError(f"paper_id {paper_id} not in corpus or has no arxiv_id")
        return r[0]

    def _slot(self, source: str, source_id: str) -> Path:
        return self.cache_dir / source / source_id.replace("/", "_")

    def resolve(self, paper_id: str | None = None, arxiv_id: str | None = None) -> FullTextDocument:
        if arxiv_id is None:
            arxiv_id = self._arxiv_id_of(paper_id)
        slot = self._slot("arxiv", arxiv_id)
        meta_p, text_p, fail_p = slot / "metadata.json", slot / "text.txt", slot / "failure.json"
        if meta_p.exists():                                   # cache hit: no network (§9)
            meta = json.loads(meta_p.read_text())
            return FullTextDocument(paper_id=paper_id, text=text_p.read_text(), **meta)
        if fail_p.exists():
            prev = json.loads(fail_p.read_text())
            raise RuntimeError(f"previous failure for {arxiv_id} (rm {fail_p} to retry): {prev['error']}")
        slot.mkdir(parents=True, exist_ok=True)
        try:
            raw = self.provider.fetch(arxiv_id)
            text, fmt = parse_eprint(raw.payload)
            if len(text) < 500:
                raise ValueError(f"parsed text too short ({len(text)} chars)")
        except Exception as e:
            # 재시도로도 살아나지 않은 일시적 오류(429·타임아웃 등)는 동결하지 않는다.
            # 동결하면 arXiv가 잠깐 막았다는 이유만으로 그 논문이 이후 모든 실행에서
            # 영구히 pool 밖으로 빠져 pool 구성이 실행 시점에 좌우된다.
            if is_transient(e):
                log.error("fulltext 일시적 실패 %s (동결 안 함, 다음 실행에서 재시도): %s", arxiv_id, e)
                raise
            fail_p.write_text(json.dumps({
                "source_id": arxiv_id, "error": f"{type(e).__name__}: {e}",
                "parser_version": PARSER_VERSION,
                "failed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=2))
            log.error("fulltext failure %s: %s", arxiv_id, e)
            raise
        meta = {
            "source": raw.source, "source_id": raw.source_id, "version": raw.version,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "parser_version": PARSER_VERSION, "source_format": fmt,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
        text_p.write_text(text)
        meta_p.write_text(json.dumps(meta, indent=2))
        log.info("cached %s%s (%s, %d chars, sha %s)", arxiv_id, raw.version, fmt, len(text), meta["sha256"][:12])
        return FullTextDocument(paper_id=paper_id, text=text, **meta)
