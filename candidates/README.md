# candidates/ — Benchmark GT survey 후보 등록소

설계 문서: `docs/benchmark-topic-selection.md`. 후보 1건 = 디렉터리 1개.

```
candidates/<domain>/<slug>/
├── candidate.yaml   ← 사람이 작성 (아래 스키마)
└── refs.json        ← scripts/extract_gt_refs.py 가 생성 (수정 금지)
```

domain ∈ {ai, se, security, systems, db}

## candidate.yaml 스키마

```yaml
topic: Terminal Agents            # agent에 줄 survey 주제 (사람이 다듬은 표현)
domain: se
gt:
  arxiv_id: "2608.20485"          # arXiv 후보면 base id (버전 없이)
  doi: null                       # CSUR 등 저널 후보면 DOI (arxiv_id 없이 가능)
  title: "Terminal Agents: A Survey of AI Agents in Command-Line Environments"
  published: "2026-08-20"
notes: ""                         # venue, 선정 근거 등 자유 기입
```

## 워크플로

```bash
PY=/data2/chanjoong/miniforge3/envs/asg-corpus/bin/python
$PY scripts/extract_gt_refs.py --candidate candidates/se/terminal-agents   # ref 추출 (S2 API)
$PY scripts/audit_candidates.py --cutoff 2025-12-31                        # 전체 후보 일괄 감사
```

감사 결과는 `data/audit/candidates_report.json` + 콘솔 표.
판정 기준(문서 §1): post-cutoff ref 비율 < 15%, eligible coverage(arXiv-resolvable 기준) ≥ 85%,
도메인별 no_cs_topic 유실 < 10% (D1 재검토 조건).
DOI 전용 후보(CSUR 등)는 감사가 corpus에서 preprint 쌍둥이(제목 정규화 일치)를 찾아 경고한다 —
발견되면 그 arXiv id를 최종 view의 exclude 목록에 반드시 포함할 것.
