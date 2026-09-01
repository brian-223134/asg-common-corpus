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

---

# 후보 선정 기준과 방식 (2026-09-01 확정)

설계 배경·임계값의 근거는 `docs/benchmark-topic-selection.md` (로컬 전용).
아래는 현재 등록된 후보 집합(27편)이 **어떻게 선정되었는지**의 기록이다.

## 1. 모집단 (candidate pool)

**ACM Computing Surveys(CSUR, ISSN 0360-0300) 2026-01-01 ~ 2026-08-31 게재분 259편 전수**
(Crossref API로 수집, DOI·게재일·ref 수 확보).

CSUR을 1차 모집단으로 삼은 이유:
- **품질 신호**: 2026년 신간은 citation이 구조적으로 무정보(수개월 차)라 인용수를 품질 기준으로
  쓸 수 없다. CSUR는 peer-review 통과 자체가 citation을 대체하는 품질 신호다 (지도교수 권고와 일치).
- **temporal 적합성**: `T_corpus(2025-12-31) < T_survey` 요건을 2026년 게재가 자동 충족하고,
  CSUR의 긴 심사 주기 덕에 문헌 창(실제 인용 문헌의 시기)은 대체로 cutoff 이전이라
  post-cutoff 검사를 통과하기 쉽다.
- **보충 모집단**: 특정 도메인에서 통과 후보가 5편 미만이면 arXiv 2026년 초 survey
  (도메인별 카테고리 + title 검색)로 보충한다. 단 arXiv 신간은 post-cutoff ref 비율이
  높은 경향이 실측됨 (se/terminal-agents: 44% → 탈락).

## 2. 도메인 분류

5개 도메인(ai · se · security · systems · db)은 제목 기반으로 수동 분류했다.
경계 사례 규칙:
- ML 기법을 다루더라도 **문제가 속한 분야**를 따른다 (예: "DP Federated Learning" → security,
  "GPU-Centric Communication" → systems).
- **[D5, 2026-09-01] 도메인 = 각 분야의 arXiv-활성 하위영역**: ai · security(ML-security) ·
  se(code intelligence/LLM4SE) · db(data-centric ML/LLM+data) · systems(ML 인프라 — 분산 학습·서빙·
  추론 최적화·GPU 인프라). 정통 OS/DS·암호·전통 SE는 universe 밖(한계로 명시). 이전의
  "ML-workload 시스템 → ai" 규칙은 폐기.
- 비-CS 응용 분야(의료·재료·음악·사회과학 응용)와 하드웨어 설계(EDA·실리콘·FPGA)는 제외 —
  대상 agent들의 corpus(CS arXiv)와 문헌 생태가 다르다.

## 3. 포함 기준 (사전 필터, 사람이 적용)

| 기준 | 값 | 근거 |
|---|---|---|
| 게재 시기 | 2026 상반기 우선 | 문헌 창이 cutoff 이전일 확률 (CSUR 심사 지연) |
| ref 수 | 60~300 (Crossref references-count) | difficulty 균형화 축, 극단값 배제 |
| 문헌 생태 | **arXiv 친화적 topic** | corpus가 arXiv-backed CS라서(결정 D1). 실측 반례: TLS revocation은 인용의 대부분이 비-arXiv(IEEE/RFC류)라 eligible 7%로 탈락 |
| 도메인 대표성 | 도메인당 5~6편, 하위 주제 중복 회피 | 최종 5편 선정의 여유분 |

⚠ "arXiv 친화적"이라는 기준은 corpus 정의(D1)에서 파생된 **의도된 편향**이다 — Security/Systems의
전통(비-arXiv) 하위 분야는 이 벤치마크의 universe 밖이며, 이는 결과 해석 시 명시되어야 한다.

## 4. 판정 게이트 (자동, scripts/audit_candidates.py)

사전 필터를 통과해 등록된 후보는 전부 다음 자동 판정을 거친다. **사람의 재량이 개입하지 않는다.**

| 게이트 | 임계 | 측정 |
|---|---|---|
| post-cutoff ref 비율 | < 15% | S2 publicationDate 또는 arXiv id 연월 |
| eligible coverage | ≥ 85% | 식별 가능 ref(arXiv id ∨ DOI) 중 corpus 수록 ∧ cutoff 이내 |
| D1 (도메인 평균) | no_cs_topic 유실 < 10% | 미수록 arXiv ref의 원인 분해 |
| preprint 쌍둥이 | 발견 시 exclude 목록 추가 | corpus 제목 정규화 일치 |

ref 추출은 3단 체인: S2 Graph API(키) → arXiv e-print .bbl/.bib → Crossref 기탁 ref.
Crossref fallback은 arXiv id 식별률이 낮아(~50%) 수치가 하한임 — S2 색인 후 재추출로 개선 가능.

## 5. 최종 5편 선정 규칙

도메인별 pass 후보 중에서: ① eligible coverage 내림차순 ② 하위 주제 다양성(같은 축 중복 회피)
③ ref 수가 60~300 중앙에 가까운 순. 동률이면 게재일이 이른 쪽.
최종 25편의 GT id(+ 쌍둥이 arXiv id)는 view의 `--exclude-file`로 등록한다.

## 6. 기록 원칙

- 탈락 후보도 refs.json과 감사 결과를 **삭제하지 않고 보존**한다 (탈락 사유가 곧 벤치마크 문서의 근거).
- 감사 결과: `data/audit/candidates_report.json` (실행마다 갱신).
- 최종 선정표는 확정 시 이 디렉터리에 `SELECTION.md`로 고정한다.

## 7. 1차 전수 감사 결과 (2026-09-01)

32편 감사 완료: 통과 1편(ai/instruction-tuning-llms, eligible 89%). 주 탈락 원인은 post-cutoff가
아니라 eligible coverage(비-arXiv venue 문헌). 원인 분석과 처리 안건(선정층 vs corpus층)은
`docs/benchmark-topic-selection.md` §4, 수치는 `data/audit/candidates_report.json`.
