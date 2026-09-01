"""후보 GT 일괄 감사 (docs/benchmark-topic-selection.md ②③).

candidates/**/refs.json을 읽어 후보별로:
- post-cutoff ref 비율 (S2 publicationDate, 없으면 arXiv id 연월)
- corpus 수록/eligible coverage (분모 2종: 전체 ref / arXiv-resolvable ref)
- 미수록 arXiv ref의 원인 분해 (no_cs_topic / dropped_by_filters / not_linked) — 도메인별 D1 지표
- DOI 전용 GT의 corpus 내 preprint 쌍둥이 탐지 (제목 정규화 일치)
usage: python scripts/audit_candidates.py [--cutoff 2025-12-31] [--corpus data/corpus/v0.1-poc]
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from datetime import date, timedelta
from pathlib import Path

from common_corpus.config import PROJECT_ROOT, load_upstream
from common_corpus.logging_utils import setup_logging
from common_corpus.providers.science_lake import ScienceLakeClient

log = logging.getLogger("audit_cand")
THRESH_POST_CUTOFF = 0.15
THRESH_ELIGIBLE = 0.85
THRESH_D1 = 0.10


def norm_title(t: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def month_end(d: date) -> date:
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def ref_date(r: dict) -> date | None:
    if r.get("publicationDate"):
        return date.fromisoformat(r["publicationDate"])
    aid = r.get("arxiv_id")
    if aid and re.match(r"^\d{4}\.", aid):
        return date(2000 + int(aid[:2]), int(aid[2:4]), 1)
    if r.get("year"):
        return date(int(r["year"]), 12, 31)
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", default="2025-12-31")
    ap.add_argument("--corpus", default="data/corpus/v0.1-poc")
    ap.add_argument("--candidates", default="candidates")
    args = ap.parse_args()
    setup_logging("audit_candidates")
    cutoff = date.fromisoformat(args.cutoff)
    corpus = PROJECT_ROOT / args.corpus
    cands = sorted(Path(args.candidates).glob("*/*/refs.json"))
    if not cands:
        raise SystemExit("refs.json이 없음 — extract_gt_refs.py 먼저")
    log.info("candidates: %d, cutoff: %s", len(cands), cutoff)

    c = ScienceLakeClient(load_upstream(), mode="local", threads=32)
    con = c.con
    all_arxiv = sorted({r["arxiv_id"] for f in cands for r in json.loads(f.read_text())["refs"] if r.get("arxiv_id")})
    all_dois = sorted({r["doi"].lower() for f in cands for r in json.loads(f.read_text())["refs"] if r.get("doi")})
    con.execute("CREATE TEMP TABLE refs (arxiv_id VARCHAR)")
    con.executemany("INSERT INTO refs VALUES (?)", [(a,) for a in all_arxiv])
    con.execute("CREATE TEMP TABLE ref_dois (doi VARCHAR)")
    if all_dois:
        con.executemany("INSERT INTO ref_dois VALUES (?)", [(d,) for d in all_dois])
    in_corpus = {r[0]: (r[1], r[2]) for r in con.sql(f"""
        SELECT r.arxiv_id, p.first_public_date, p.date_precision
        FROM refs r JOIN '{corpus}/papers.parquet' p USING (arxiv_id)""").fetchall()}
    doi_in_corpus = {r[0]: (r[1], r[2]) for r in con.sql(f"""
        SELECT d.doi, p.first_public_date, p.date_precision
        FROM ref_dois d JOIN '{corpus}/papers.parquet' p USING (doi)""").fetchall()}
    # 미수록 arXiv ref 원인 분해 (audit_coverage.py와 동일 로직)
    con.execute(r"""
        CREATE TEMP TABLE ref_oa AS
        SELECT DISTINCT lower(regexp_extract(coalesce(pdf_url,'')||' '||coalesce(landing_page_url,''),
            'arxiv\.org/(?:abs|pdf)/((?:\d{4}\.\d{4,5}|[a-zA-Z-]+(?:\.[a-zA-Z]{2})?/\d{7}))', 1)) AS arxiv_id, work_id
        FROM openalex.works_locations
        WHERE pdf_url LIKE '%arxiv.org%' OR landing_page_url LIKE '%arxiv.org%'""")
    con.execute("CREATE TEMP TABLE hit AS SELECT DISTINCT r.arxiv_id, o.work_id FROM refs r JOIN ref_oa o USING (arxiv_id)")
    cs_set = {r[0] for r in con.sql("""
        SELECT DISTINCT h.arxiv_id FROM hit h
        JOIN openalex.works_topics wt ON h.work_id = wt.work_id
        JOIN openalex.topics t ON wt.topic_id = t.id AND t.field_display_name='Computer Science'""").fetchall()}
    linked = {r[0] for r in con.sql("SELECT DISTINCT arxiv_id FROM hit").fetchall()}

    def classify(aid: str) -> str:
        if aid in in_corpus:
            return "in_corpus"
        if aid in cs_set:
            return "dropped_by_filters"
        if aid in linked:
            return "no_cs_topic"
        return "not_linked_in_openalex"

    corpus_titles = None  # lazy: DOI 전용 GT가 있을 때만 적재
    rows, domain_stats = [], {}
    import yaml
    for f in cands:
        d = json.loads(f.read_text())
        refs = d["refs"]
        cand = yaml.safe_load((f.parent / "candidate.yaml").read_text())  # 정본은 yaml (재분류 반영)
        dom, gt = cand["domain"], cand["gt"]
        n = len(refs)
        arx = [r["arxiv_id"] for r in refs if r.get("arxiv_id")]
        identifiable = [r for r in refs if r.get("arxiv_id") or r.get("doi")]
        dates = [ref_date(r) for r in refs]
        post = sum(1 for x in dates if x and x > cutoff)
        cls = {k: 0 for k in ("in_corpus", "dropped_by_filters", "no_cs_topic", "not_linked_in_openalex", "doi_not_in_corpus")}
        eligible = 0
        for r in identifiable:
            a, d = r.get("arxiv_id"), (r.get("doi") or "").lower()
            if a:
                st = classify(a)
                hit = in_corpus.get(a)
            elif d in doi_in_corpus:
                st, hit = "in_corpus", doi_in_corpus[d]
            else:
                st, hit = "doi_not_in_corpus", None   # 대부분 비-arXiv venue — corpus 정의 밖
            cls[st] += 1
            if st == "in_corpus" and hit:
                fpd, prec = hit
                if fpd and (month_end(fpd) if prec == "month" else fpd) <= cutoff:
                    eligible += 1
        twin = None
        if not gt.get("arxiv_id"):
            if corpus_titles is None:
                corpus_titles = {r[0]: r[1] for r in con.sql(f"""
                    SELECT regexp_replace(lower(title),'[^a-z0-9]','','g'), arxiv_id
                    FROM '{corpus}/papers.parquet'""").fetchall()}
            twin = corpus_titles.get(norm_title(gt.get("title")))
        row = {
            "domain": dom, "slug": f.parent.name, "topic": cand["topic"],
            "gt_id": gt.get("arxiv_id") or gt.get("doi"), "gt_published": gt.get("published"),
            "refs": n, "arxiv_resolvable": len(arx), "identifiable": len(identifiable),
            "post_cutoff_ratio": round(post / max(n, 1), 3),
            **cls,
            "eligible": eligible,
            "eligible_coverage_arxiv": round(eligible / max(len(arx), 1), 3) if arx else None,
            "eligible_coverage_identifiable": round(eligible / max(len(identifiable), 1), 3),
            "eligible_coverage_all": round(eligible / max(n, 1), 3),
            "no_cs_topic_ratio_arxiv": round(cls["no_cs_topic"] / max(len(arx), 1), 3),
            "preprint_twin_in_corpus": twin,
            "pass": (post / max(n, 1) < THRESH_POST_CUTOFF) and (eligible / max(len(identifiable), 1) >= THRESH_ELIGIBLE),
        }
        rows.append(row)
        s = domain_stats.setdefault(dom, {"n": 0, "no_cs_sum": 0.0})
        s["n"] += 1
        s["no_cs_sum"] += row["no_cs_topic_ratio_arxiv"]
        log.info("[%s/%s] refs=%d(식별 %d, arXiv %d) post_cutoff=%.0f%% eligible(식별)=%.0f%% no_cs=%.0f%% doi_miss=%d pass=%s%s",
                 dom, f.parent.name, n, len(identifiable), len(arx), 100 * row["post_cutoff_ratio"],
                 100 * row["eligible_coverage_identifiable"], 100 * row["no_cs_topic_ratio_arxiv"],
                 cls["doi_not_in_corpus"], row["pass"], f" ⚠twin={twin}" if twin else "")

    d1 = {dom: round(s["no_cs_sum"] / s["n"], 4) for dom, s in domain_stats.items()}
    for dom, v in d1.items():
        log.info("D1 도메인 평균 no_cs_topic 유실 [%s]: %.1f%% (임계 %.0f%%)%s",
                 dom, 100 * v, 100 * THRESH_D1, " ⚠ 초과 — D1 재논의 대상" if v > THRESH_D1 else "")
    out = PROJECT_ROOT / "data" / "audit" / "candidates_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "cutoff": args.cutoff, "thresholds": {"post_cutoff": THRESH_POST_CUTOFF, "eligible": THRESH_ELIGIBLE, "d1": THRESH_D1},
        "d1_by_domain": d1, "candidates": rows}, indent=2, ensure_ascii=False))
    log.info("written: %s", out)


if __name__ == "__main__":
    main()
