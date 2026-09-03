"""FullTextProvider implementations (spec §8.6). v1: arXiv only."""
from __future__ import annotations

import logging
import re
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

log = logging.getLogger("fulltext.provider")
UA = {"User-Agent": "asg-common-corpus/0.1 (research; kimchanjoong54@gmail.com)"}

# 재시도해도 결과가 달라지지 않는 오류(404, 파싱 실패)와 구분한다. 이 구분이
# resolver의 실패 동결 여부를 결정하므로 두 곳에서 같은 판정을 쓴다.
TRANSIENT_HTTP_CODES = frozenset({429, 500, 502, 503, 504})


def is_transient(e: BaseException) -> bool:
    if isinstance(e, urllib.error.HTTPError):
        return e.code in TRANSIENT_HTTP_CODES
    return isinstance(e, (TimeoutError, socket.timeout, urllib.error.URLError, ConnectionError))


@dataclass(frozen=True)
class RawFullText:
    source: str          # "arxiv"
    source_id: str       # base arXiv id
    version: str         # "v3"
    payload: bytes       # raw e-print bytes


class ArxivFullTextProvider:
    """LaTeX 소스 우선 (SurveyX 재현 설계 §4.3). e-print가 PDF뿐이면 parser가 pdftotext로 처리."""

    name = "arxiv"

    def __init__(self, delay_seconds: float = 3.0, max_retries: int = 4,
                 backoff_seconds: float = 15.0):
        self.delay = delay_seconds
        self.max_retries = max_retries
        self.backoff = backoff_seconds
        self._last = 0.0

    def _get_once(self, url: str) -> tuple[bytes, dict]:
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read(), dict(r.headers)
        finally:
            # 실패해도 마지막 요청 시각을 갱신한다. 예외 경로에서 갱신을 빠뜨리면
            # 다음 요청이 딜레이 없이 즉시 나가 429 폭주로 이어진다.
            self._last = time.monotonic()

    def _get(self, url: str) -> tuple[bytes, dict]:
        """429·타임아웃은 arXiv 쪽 일시적 상태다. 지수 백오프로 재시도한다 —
        여기서 그대로 포기하면 resolver가 실패를 캐시에 영구 동결해(§21)
        그 논문이 이후 모든 실행에서 pool 밖으로 밀려난다."""
        for attempt in range(self.max_retries + 1):
            try:
                return self._get_once(url)
            except Exception as e:
                if not is_transient(e) or attempt == self.max_retries:
                    raise
                nap = self.backoff * (2 ** attempt)
                log.warning("일시적 오류 %s (%s) — %.0fs 후 재시도 (%d/%d)",
                            e, url, nap, attempt + 1, self.max_retries)
                time.sleep(nap)
        raise AssertionError("unreachable")

    def latest_version(self, arxiv_id: str) -> str:
        xml, _ = self._get(f"https://export.arxiv.org/api/query?id_list={arxiv_id}")
        m = re.search(rf"<id>https?://arxiv\.org/abs/{re.escape(arxiv_id)}(v\d+)</id>",
                      xml.decode("utf-8", "replace"))
        if not m:
            raise LookupError(f"arXiv API has no entry for {arxiv_id}")
        return m.group(1)

    def fetch(self, arxiv_id: str, version: str | None = None) -> RawFullText:
        if version:
            payload, headers = self._get(f"https://arxiv.org/e-print/{arxiv_id}{version}")
            v = version
        else:
            # 버전을 지정하지 않으면 e-print가 최신판으로 리다이렉트하고 실제 버전을
            # content-disposition(arXiv-<id>v<n>.tar.gz)에 실어준다. 이 한 번의 요청으로
            # 버전 확인까지 끝나므로 논문당 요청이 2회 → 1회가 되고, 429를 자주 내는
            # export.arxiv.org API를 아예 거치지 않는다.
            payload, headers = self._get(f"https://arxiv.org/e-print/{arxiv_id}")
            m = re.search(rf"{re.escape(arxiv_id)}(v\d+)",
                          headers.get("Content-Disposition", "") or "")
            v = m.group(1) if m else self.latest_version(arxiv_id)
        log.info("fetched %s%s (%d bytes)", arxiv_id, v, len(payload))
        return RawFullText(source=self.name, source_id=arxiv_id, version=v, payload=payload)
