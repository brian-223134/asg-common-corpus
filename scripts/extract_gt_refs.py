"""후보 GT survey의 reference 목록 추출 → candidates/<domain>/<slug>/refs.json

소스: ① Semantic Scholar Graph API → ② S2 미색인(신간에 흔함)이고 arXiv GT면
arXiv e-print의 .bbl/bibitem·.bib 파싱으로 fallback (B5 provider 재사용, title은 미확보).
usage: python scripts/extract_gt_refs.py --candidate candidates/se/terminal-agents
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

from common_corpus.logging_utils import setup_logging
from common_corpus.models import normalize_arxiv_id

log = logging.getLogger("extract_refs")
S2 = "https://api.semanticscholar.org/graph/v1/paper/"
FIELDS = "title,externalIds,publicationDate,year"
UA = {"User-Agent": "asg-common-corpus/0.1 (research; kimchanjoong54@gmail.com)"}


def _s2_headers() -> dict:
    import os
    key = os.environ.get("S2_API_KEY")
    if not key:  # 프로젝트 .env fallback (미커밋)
        envf = Path(__file__).resolve().parents[1] / ".env"
        if envf.exists():
            for line in envf.read_text().splitlines():
                if line.startswith("S2_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    h = dict(UA)
    if key:
        h["x-api-key"] = key
    return h

BIB_ARXIV = re.compile(
    r"(?:arXiv[:.\s/]*|arxiv\.org/(?:abs|pdf)/)"
    r"((?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Za-z]{2})?/\d{7}))", re.I)
BIB_DOI = re.compile(r"\b10\.\d{4,9}/[^\s,}{\\\"']+")


def s2_get(path: str, params: dict, tries: int = 8) -> dict:
    """키 사용 시도 -> 429면 익명으로 전환 (2026-09-01 실측: 키가 쿼터 제한, 익명은 통과)."""
    url = S2 + path + "?" + urllib.parse.urlencode(params)
    keyed = _s2_headers()
    variants = [keyed, UA] if "x-api-key" in keyed else [UA]
    for i in range(tries):
        headers = variants[min(i, len(variants) - 1)]
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < tries - 1:
                wait = 3 if i == 0 and len(variants) > 1 else min(10 * 2 ** i, 180)
                log.warning("S2 %s (%s) — %ds 후 재시도 (%d/%d)", e.code,
                            "keyed" if "x-api-key" in headers else "anon", wait, i + 1, tries)
                time.sleep(wait)
                continue
            raise


def extract_s2(gt_key: str) -> dict:
    meta = s2_get(gt_key, {"fields": "title,publicationDate,year,externalIds,referenceCount,venue"})
    if not meta.get("referenceCount"):
        log.warning("S2 referenceCount=%s — references 호출 생략", meta.get("referenceCount"))
        return {"gt_s2": meta, "refs": []}
    refs, offset = [], 0
    while True:
        page = s2_get(f"{gt_key}/references", {"fields": FIELDS, "limit": 500, "offset": offset})
        for it in page.get("data") or []:
            p = it.get("citedPaper") or {}
            ext = p.get("externalIds") or {}
            refs.append({
                "title": p.get("title"),
                "arxiv_id": normalize_arxiv_id(ext.get("ArXiv")),
                "doi": (ext.get("DOI") or None),
                "publicationDate": p.get("publicationDate"),
                "year": p.get("year"),
            })
        offset = page.get("next")
        if offset is None:
            break
        time.sleep(1.5)
    return {"gt_s2": meta, "refs": refs}


def extract_from_arxiv_source(arxiv_id: str) -> dict:
    """e-print의 .bbl(bibitem) 또는 .bib(@entry)에서 ref 추출."""
    import gzip
    import io
    import tarfile

    from common_corpus.fulltext.providers import ArxivFullTextProvider

    blob = ArxivFullTextProvider().fetch(arxiv_id).payload
    try:
        data = gzip.decompress(blob)
    except OSError:
        data = blob
    try:
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            members = {m.name: tf.extractfile(m).read()
                       for m in tf.getmembers() if m.isfile() and m.size < 20_000_000}
    except tarfile.TarError:
        members = {"main.tex": data}

    items: list[str] = []
    bbl_texts = [b.decode("utf-8", "replace") for n, b in members.items() if n.lower().endswith(".bbl")]
    if not bbl_texts:  # bibitem이 tex 본문에 인라인된 경우
        bbl_texts = [b.decode("utf-8", "replace") for n, b in members.items()
                     if n.lower().endswith(".tex") and b"\\bibitem" in b]
    for t in bbl_texts:
        items.extend(re.split(r"\\bibitem", t)[1:])
    src = "arxiv-src-bbl"
    if not items:
        for t in (b.decode("utf-8", "replace") for n, b in members.items() if n.lower().endswith(".bib")):
            items.extend(re.split(r"(?=@[a-zA-Z]+\s*\{)", t)[1:])
        src = "arxiv-src-bib"
    if not items:
        raise LookupError(f"{arxiv_id}: e-print에서 .bbl/.bib을 찾지 못함")
    refs = []
    for it in items:
        m = BIB_ARXIV.search(it)
        d = BIB_DOI.search(it)
        refs.append({"title": None,
                     "arxiv_id": normalize_arxiv_id(m.group(1)) if m else None,
                     "doi": d.group(0).rstrip(".") if d else None,
                     "publicationDate": None, "year": None})
    return {"refs": refs, "source": src}


def extract_from_crossref(doi: str) -> dict:
    """Crossref 기탁 reference 목록 (ACM 등 대부분의 저널이 기탁). arXiv id는 unstructured에서 추출."""
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi) + "?mailto=kimchanjoong54@gmail.com"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        msg = json.load(r)["message"]
    refs = []
    for it in msg.get("reference") or []:
        blob = " ".join(str(v) for v in it.values())
        m = BIB_ARXIV.search(blob)
        y = it.get("year")
        refs.append({"title": it.get("article-title") or it.get("volume-title"),
                     "arxiv_id": normalize_arxiv_id(m.group(1)) if m else None,
                     "doi": (it.get("DOI") or "").lower() or None,
                     "publicationDate": None,
                     "year": int(y) if y and str(y).isdigit() else None})
    if not refs:
        raise LookupError(f"{doi}: Crossref에 기탁된 reference 없음")
    return {"refs": refs, "source": "crossref-deposited"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True, help="candidates/<domain>/<slug> 디렉터리")
    args = ap.parse_args()
    setup_logging("extract_refs")
    cdir = Path(args.candidate)
    cand = yaml.safe_load((cdir / "candidate.yaml").read_text())
    gt = cand["gt"]
    if gt.get("arxiv_id"):
        key = f"arXiv:{gt['arxiv_id']}"
    elif gt.get("doi"):
        key = f"DOI:{gt['doi']}"
    else:
        raise SystemExit("candidate.yaml gt에 arxiv_id 또는 doi가 필요")
    log.info("extracting refs for %s (%s)", cdir, key)
    import urllib.error
    try:
        out = extract_s2(key)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        log.warning("S2 404 (미색인) — fallback으로 진행")
        out = {"gt_s2": {"note": "s2-404"}, "refs": []}
    source = "semanticscholar-graph-api"
    if not out["refs"] and gt.get("arxiv_id"):
        log.warning("S2 references 미색인 — arXiv 소스 파싱으로 fallback")
        fb = extract_from_arxiv_source(gt["arxiv_id"])
        out["refs"] = fb["refs"]
        source = fb["source"]
    elif not out["refs"] and gt.get("doi"):
        log.warning("S2 references 미색인 — Crossref 기탁 ref로 fallback")
        fb = extract_from_crossref(gt["doi"])
        out["refs"] = fb["refs"]
        source = fb["source"]
    n = len(out["refs"])
    n_ax = sum(1 for r in out["refs"] if r["arxiv_id"])
    result = {
        "candidate": cand,
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "summary": {"refs": n, "arxiv_resolvable": n_ax,
                    "doi_only": sum(1 for r in out["refs"] if r["doi"] and not r["arxiv_id"]),
                    "unresolved": sum(1 for r in out["refs"] if not r["doi"] and not r["arxiv_id"])},
        "gt_s2": out["gt_s2"],
        "refs": out["refs"],
    }
    (cdir / "refs.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    log.info("refs=%d (arXiv %d, %.0f%%) source=%s → %s", n, n_ax, 100 * n_ax / max(n, 1), source, cdir / "refs.json")


if __name__ == "__main__":
    main()
