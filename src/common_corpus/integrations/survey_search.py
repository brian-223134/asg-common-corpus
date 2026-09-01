"""B6 — CorpusView를 agent가 소비하는 DB 포맷으로 내보내기.

포맷 (docs/integration-guide.md §2, §5) — 두 agent 모두 TinyDB 테이블명 'cs_paper_info'를 읽는다:
- autosurvey  : {"cs_paper_info": {"1": {id,title,url,date,abs,cat}}}
- surveyforge : 위 + citation_count

임베딩/FAISS 생성은 여기서 하지 않는다 — agent별 임베딩 모델이 통제 변수이므로
각 agent의 빌드 스크립트(AutoSurvey scripts/build_index.py 등)에 위임한다.
id는 버전 접미사 없는 arXiv base id다(기존 DB는 '1811.06122v1' 형식이었음 — 어댑터 유의).
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from common_corpus.config import PROJECT_ROOT

log = logging.getLogger("export")

FORMATS = ("autosurvey", "surveyforge")


def export_agent_db(view_dir: Path, corpus_dir: Path, fmt: str, out_path: Path,
                    limit: int | None = None) -> Path:
    assert fmt in FORMATS, fmt
    view_manifest = json.loads((Path(view_dir) / "view_manifest.json").read_text())
    con = duckdb.connect()
    lim = f"LIMIT {int(limit)}" if limit else ""
    rows = con.sql(f"""
        WITH cat AS (
            SELECT paper_id, arg_max(subfield, score) AS subfield
            FROM '{corpus_dir}/paper_topics.parquet' GROUP BY paper_id
        )
        SELECT p.arxiv_id, p.title, p.abstract, p.first_public_date, p.citation_count, c.subfield
        FROM '{corpus_dir}/papers.parquet' p
        JOIN '{view_dir}/paper_ids.parquet' v USING (paper_id)
        LEFT JOIN cat c USING (paper_id)
        ORDER BY p.paper_id {lim}
    """).fetchall()
    log.info("exporting %d records as %s", len(rows), fmt)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write('{"cs_paper_info": {')
        for i, (aid, title, abstract, fpd, cc, subfield) in enumerate(rows, start=1):
            rec = {
                "id": aid,
                "title": title,
                "url": f"http://arxiv.org/abs/{aid}",
                "date": fpd.isoformat() if fpd else None,
                "abs": abstract,
                "cat": subfield,
            }
            if fmt == "surveyforge":
                rec["citation_count"] = cc
            chunk = ("," if i > 1 else "") + json.dumps(str(i)) + ": " + json.dumps(rec, ensure_ascii=False)
            f.write(chunk)
            h.update(chunk.encode())
        f.write("}}")
    # content_sha256(h)은 레코드 청크만 덮고 JSON 껍데기('{"cs_paper_info": {', '}}')
    # 를 제외한다 — 파일 지문이 아니다. 소비자가 sha256sum으로 그대로 대조할 수
    # 있도록 파일 전체 해시를 따로 싣는다 (SurveyForge 빌드가 이 차이를 파일
    # 지문으로 오독해 중단된 적 있음, 2026-08-31).
    fh = hashlib.sha256()
    with open(out_path, "rb") as rf:
        for blk in iter(lambda: rf.read(1 << 24), b""):
            fh.update(blk)
    manifest = {
        "format": fmt,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "records": len(rows),
        "content_sha256": h.hexdigest(),
        "file_sha256": fh.hexdigest(),
        "view": {"name": view_manifest["view_name"], "files_sha256": view_manifest["files_sha256"]},
        "base_corpus_sha256": view_manifest["base_corpus"]["papers_sha256"],
        "id_convention": "arxiv base id (no version suffix)",
    }
    mp = out_path.with_suffix(out_path.suffix + ".manifest.json")
    mp.write_text(json.dumps(manifest, indent=2))
    log.info("wrote %s (+manifest %s)", out_path, mp.name)
    return out_path
