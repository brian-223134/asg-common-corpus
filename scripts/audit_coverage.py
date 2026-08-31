"""GT reference coverage audit (spec §19) — SurveyBench(10) + SurGE(170).

각 GT survey의 인용(arXiv base id)이 corpus에 얼마나 있는지, 없다면 왜 없는지
(OpenAlex 미연결 / CS topic 불일치 / 품질 필터)를 분해한다. D1 재검토 조건
(분류 불일치 유실 topic 평균 10% 초과 여부)도 여기서 측정한다.
usage: python scripts/audit_coverage.py [--corpus data/corpus/v0.1-poc]
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from common_corpus.config import PROJECT_ROOT, load_upstream
from common_corpus.logging_utils import setup_logging
from common_corpus.providers.science_lake import ScienceLakeClient

log = logging.getLogger("audit")
SB_DIR = Path("/data2/chanjoong/survey-agent/SurveyForge/SurveyBench/ref_bench")
SURGE_GOLD = Path("/data2/chanjoong/survey-agent/survey-search/data/surge_gold.json")


def load_benchmarks() -> list[dict]:
    topics = []
    for f in sorted(SB_DIR.glob("*_bench.json")):
        refs = sorted(json.loads(f.read_text()).keys())
        topics.append({"bench": "surveybench", "topic": f.stem.replace("_bench", ""), "date": None, "refs": refs})
    gold = json.loads(SURGE_GOLD.read_text())
    for e in gold["topics"] if "topics" in gold else gold[[k for k in gold if k != "stats"][0]]:
        topics.append({"bench": "surge", "topic": e["topic"], "date": e.get("date"), "refs": sorted(set(e["gold_ids"]))})
    return topics


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/corpus/v0.1-poc")
    args = ap.parse_args()
    setup_logging("audit_coverage")
    corpus = PROJECT_ROOT / args.corpus
    topics = load_benchmarks()
    all_refs = sorted({r for t in topics for r in t["refs"]})
    log.info("topics: %d (surveybench %d, surge %d), distinct refs: %d",
             len(topics), sum(t['bench'] == 'surveybench' for t in topics),
             sum(t['bench'] == 'surge' for t in topics), len(all_refs))

    c = ScienceLakeClient(load_upstream(), mode="local", threads=32)
    con = c.con
    con.execute("CREATE TEMP TABLE refs (arxiv_id VARCHAR)")
    con.executemany("INSERT INTO refs VALUES (?)", [(r,) for r in all_refs])

    # ref별 상태 분류 (우선순위: in_corpus > filtered > no_cs_topic > not_linked)
    con.execute(f"""
        CREATE TEMP TABLE ref_corpus AS
        SELECT r.arxiv_id, p.paper_id, p.first_public_date, p.date_precision
        FROM refs r JOIN '{corpus}/papers.parquet' p USING (arxiv_id)
    """)
    log.info("in corpus: %d", con.sql("SELECT count(*) FROM ref_corpus").fetchone()[0])
    con.execute(r"""
        CREATE TEMP TABLE ref_oa AS
        SELECT DISTINCT lower(regexp_extract(coalesce(pdf_url,'')||' '||coalesce(landing_page_url,''),
            'arxiv\.org/(?:abs|pdf)/((?:\d{4}\.\d{4,5}|[a-zA-Z-]+(?:\.[a-zA-Z]{2})?/\d{7}))', 1)) AS arxiv_id,
            work_id
        FROM openalex.works_locations
        WHERE (pdf_url LIKE '%arxiv.org%' OR landing_page_url LIKE '%arxiv.org%')
    """)
    con.execute("CREATE TEMP TABLE ref_oa_hit AS SELECT DISTINCT r.arxiv_id, o.work_id FROM refs r JOIN ref_oa o USING (arxiv_id)")
    con.execute("""
        CREATE TEMP TABLE ref_cs AS
        SELECT DISTINCT h.arxiv_id FROM ref_oa_hit h
        JOIN openalex.works_topics wt ON h.work_id = wt.work_id
        JOIN openalex.topics t ON wt.topic_id = t.id AND t.field_display_name = 'Computer Science'
    """)
    status = {r[0]: r[1] for r in con.sql("""
        SELECT r.arxiv_id,
               CASE WHEN c.arxiv_id IS NOT NULL THEN 'in_corpus'
                    WHEN cs.arxiv_id IS NOT NULL THEN 'dropped_by_filters'
                    WHEN h.arxiv_id IS NOT NULL THEN 'no_cs_topic'
                    ELSE 'not_linked_in_openalex' END
        FROM refs r
        LEFT JOIN (SELECT DISTINCT arxiv_id FROM ref_corpus) c USING (arxiv_id)
        LEFT JOIN ref_cs cs USING (arxiv_id)
        LEFT JOIN (SELECT DISTINCT arxiv_id FROM ref_oa_hit) h USING (arxiv_id)
    """).fetchall()}
    fpd = {r[0]: (r[1], r[2]) for r in con.sql("SELECT arxiv_id, first_public_date, date_precision FROM ref_corpus").fetchall()}

    rows, agg = [], {"in_corpus": 0, "dropped_by_filters": 0, "no_cs_topic": 0, "not_linked_in_openalex": 0}
    for t in topics:
        n = len(t["refs"])
        cnt = {k: 0 for k in agg}
        eligible = 0
        for r in t["refs"]:
            st = status[r]
            cnt[st] += 1
            if st == "in_corpus" and t["date"]:
                d, prec = fpd[r]
                from datetime import date as _d, timedelta
                cut = _d.fromisoformat(t["date"])
                if d is not None:
                    end = (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1) if prec == "month" else d
                    if end <= cut:
                        eligible += 1
        rows.append({"bench": t["bench"], "topic": t["topic"], "refs": n, **cnt,
                     "coverage": round(cnt["in_corpus"] / n, 4),
                     "no_cs_topic_ratio": round(cnt["no_cs_topic"] / n, 4),
                     "eligible_under_gt_cutoff": eligible if t["date"] else None})
        for k in agg:
            agg[k] += cnt[k]

    for bench in ("surveybench", "surge"):
        sel = [r for r in rows if r["bench"] == bench]
        mean_cov = sum(r["coverage"] for r in sel) / len(sel)
        mean_miss_cs = sum(r["no_cs_topic_ratio"] for r in sel) / len(sel)
        log.info("[%s] topics=%d mean coverage=%.1f%% mean no_cs_topic loss=%.1f%% (D1 재검토 임계 10%%)",
                 bench, len(sel), 100 * mean_cov, 100 * mean_miss_cs)
    out = PROJECT_ROOT / "data" / "audit"
    out.mkdir(parents=True, exist_ok=True)
    (out / "gt_coverage.json").write_text(json.dumps({"aggregate": agg, "topics": rows}, indent=2, ensure_ascii=False))
    log.info("aggregate over distinct refs: %s", {k: sum(1 for v in status.values() if v == k) for k in agg})
    log.info("written: %s", out / "gt_coverage.json")


if __name__ == "__main__":
    main()
