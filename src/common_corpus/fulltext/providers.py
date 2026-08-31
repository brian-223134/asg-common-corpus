"""FullTextProvider implementations (spec §8.6). v1: arXiv only."""
from __future__ import annotations

import logging
import re
import time
import urllib.request
from dataclasses import dataclass

log = logging.getLogger("fulltext.provider")
UA = {"User-Agent": "asg-common-corpus/0.1 (research; kimchanjoong54@gmail.com)"}


@dataclass(frozen=True)
class RawFullText:
    source: str          # "arxiv"
    source_id: str       # base arXiv id
    version: str         # "v3"
    payload: bytes       # raw e-print bytes


class ArxivFullTextProvider:
    """LaTeX 소스 우선 (SurveyX 재현 설계 §4.3). e-print가 PDF뿐이면 parser가 pdftotext로 처리."""

    name = "arxiv"

    def __init__(self, delay_seconds: float = 3.0):
        self.delay = delay_seconds
        self._last = 0.0

    def _get(self, url: str) -> bytes:
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        self._last = time.monotonic()
        return data

    def latest_version(self, arxiv_id: str) -> str:
        xml = self._get(f"https://export.arxiv.org/api/query?id_list={arxiv_id}").decode("utf-8", "replace")
        m = re.search(rf"<id>https?://arxiv\.org/abs/{re.escape(arxiv_id)}(v\d+)</id>", xml)
        if not m:
            raise LookupError(f"arXiv API has no entry for {arxiv_id}")
        return m.group(1)

    def fetch(self, arxiv_id: str, version: str | None = None) -> RawFullText:
        v = version or self.latest_version(arxiv_id)
        payload = self._get(f"https://arxiv.org/e-print/{arxiv_id}{v}")
        log.info("fetched %s%s (%d bytes)", arxiv_id, v, len(payload))
        return RawFullText(source=self.name, source_id=arxiv_id, version=v, payload=payload)
