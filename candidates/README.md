# candidates/ — Benchmark GT survey 후보 등록소

설계 문서: `docs/benchmark-topic-selection.md`. 후보 1건 = 디렉터리 1개.

```
candidates/<domain>/<slug>/
├── candidate.yaml   ← 사람이 작성 (아래 스키마)
└── refs.json        ← scripts/extract_gt_refs.py 가 생성 (수정 금지)
```

domain ∈ {ai, db, security, systems, network} = **선정 5개 (D9 확정)**
+ {algorithm, se} = **보류** (데이터 전량 보존, 재개 조건은 SELECTION.md §4)
db는 D6에서 보류였으나 8차 모집으로 ○7편을 확보해 보류 해제(D9).

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
판정 기준: post-cutoff ref 비율 < 15%, eligible coverage ≥ 50% ∧ eligible 절대수 ≥ 60편,
도메인별 no_cs_topic 유실 < 10% (D1 재검토 조건). 임계 완화 근거는 D5·D7.
DOI 전용 후보(CSUR 등)는 감사가 corpus에서 preprint 쌍둥이(제목 정규화 일치)를 찾아 경고한다 —
발견되면 그 arXiv id를 최종 view의 exclude 목록에 반드시 포함할 것.

---

# 후보 선정 기준과 방식 (2026-09-02 갱신)

설계 배경·임계값의 근거는 `docs/benchmark-topic-selection.md` (로컬 전용).
아래는 현재 등록된 후보 집합(105편)이 **어떻게 선정되었는지**의 기록이다.

## 1. 모집단 (candidate pool)

1차 모집단은 **ACM Computing Surveys(CSUR) 2026-01~08 게재분 259편 전수**(Crossref API).
이후 도메인 재정의(D5/D6)에 따라 **분야 대표 survey venue와 arXiv를 표적 확장**:
IEEE COMST(네트워킹의 CSUR 격) · TOSEM · TKDE · ACL Findings · arXiv cs.{SE,DB,NI,CR,DC} 2026.
발굴 도구: Crossref(저널 전수) · arXiv API(카테고리 검색) · OpenAlex API(주제 검색, arXiv 장애 시 대체).

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

도메인(ai · se · security · systems · network · db · algorithm)은 제목 기반으로 수동 분류했다.
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
| 문헌 생태 | **arXiv 친화적 topic** | corpus가 arXiv-backed CS라서(결정 D1). 실측 반례: TLS revocation 7% · vector commitment 0%(IACR 생태) — 인용의 대부분이 비-arXiv |
| 도메인 대표성 | 도메인당 5~6편, 하위 주제 중복 회피 | 최종 5편 선정의 여유분 |

⚠ "arXiv 친화적"이라는 기준은 corpus 정의(D1)에서 파생된 **의도된 편향**이다 — Security/Systems의
전통(비-arXiv) 하위 분야는 이 벤치마크의 universe 밖이며, 이는 결과 해석 시 명시되어야 한다.

## 4. 판정 게이트 (자동, scripts/audit_candidates.py)

사전 필터를 통과해 등록된 후보는 전부 다음 자동 판정을 거친다. **사람의 재량이 개입하지 않는다.**

| 게이트 | 임계 | 측정 |
|---|---|---|
| post-cutoff ref 비율 | < 15% | S2 publicationDate 또는 arXiv id 연월 |
| eligible coverage | ≥ 50% | 식별 가능 ref(arXiv id ∨ DOI) 중 corpus 수록 ∧ cutoff 이내 |
| eligible 절대수 | ≥ 60편 | 채점 분산 확보 (비율이 높아도 절대수가 적으면 변별력 부족) |
| D1 (도메인 평균) | no_cs_topic 유실 < 10% | 미수록 arXiv ref의 원인 분해 |
| preprint 쌍둥이 | 발견 시 exclude 목록 추가 | corpus 제목 정규화 일치 |

ref 추출은 3단 체인: S2 Graph API(키) → arXiv e-print .bbl/.bib → Crossref 기탁 ref.
Crossref fallback은 arXiv id 식별률이 낮아(~50%) 수치가 하한임 — S2 색인 후 재추출로 개선 가능.

## 5. 최종 5편 선정 규칙

도메인별 pass 후보 중에서: ① eligible coverage 내림차순 ② **하위 주제 다양성 — 도메인 내 같은 축 2편 초과 금지(하드 제약)**
③ ref 수가 60~300 중앙에 가까운 순. 동률이면 게재일이 이른 쪽.
②를 하드 제약으로 올린 이유: 7차까지의 systems 선정 5편이 전부 'LLM 효율' 한 축이었고,
실제로 25편 중 GT ref 중복 최댓값(6.1%, moe-inference × llm-dist-training)이 거기서 나왔다.
최종 25편의 GT id(+ 쌍둥이 arXiv id)는 view의 `--exclude-file`로 등록한다.

## 6. 기록 원칙

- 탈락 후보도 refs.json과 감사 결과를 **삭제하지 않고 보존**한다 (탈락 사유가 곧 벤치마크 문서의 근거).
- 감사 결과: `data/audit/candidates_report.json` (실행마다 갱신).
- 최종 선정표는 `SELECTION.md`로 고정됨 (2026-09-02 확정, D9). view 제외 목록은 `gt_exclude.txt`.
- 선정 25편의 topic·GT 제목·링크는 `GT-SURVEYS.md` (agent 실행 시 입력 문자열의 정본).

## 7. 모집 차수 이력과 전수 감사 결과 (2026-09-02, 최종 105편)

| 차수 | 목적 | 결과 → 배운 것 |
|---|---|---|
| 1차 (27) | CSUR 전수에서 도메인별 대표 topic | 통과 1편 — 탈락 원인은 post-cutoff가 아니라 **비-arXiv venue 정전**(eligible coverage) |
| probe (3) | 암호(HE/FHE)·HPC의 "arXiv 친화성" prior 검증 | 4~18%로 prior 실측 확정 |
| 2차 (16) | 약한 도메인을 arXiv-heavy 하위분야로 재모집 | LLM4SE·LLM-data 계열이 2~3배 높음 → **하위영역이 결정 변수** |
| 3차 (4) | 정통 OS/분산/스토리지 보강 (사용자 지적) | 4~28% — 정통 systems는 구조적 미달 확정 → D5 재정의 |
| 4차 (6) | D5 표적: TOSEM·TKDE·ACL 등 저널 GT | systems 4편 본선권 확보 |
| 5·6차 (14) | network 신설(D6): CSUR+COMST+CS측 edge | ○2 — 무선-PHY·IEEE 정전 낮음 |
| 7차 (8) | network 광역 재발굴 (AI×networking 교차) | wireless-foundation-models 60% 추가 → ○3 |
| **8차 (26)** | **D7 방침 반영 광역 모집: algorithm 신설 + db·systems 확장** | **db ○1→7 부활 · systems ○4→5 완성 · algorithm ○3. 순수 이론/비-LLM 축은 여전히 20%대** |

8차 모집원: Crossref 15개 저널(CSUR·COMST·TOSEM·TKDE·TODS·VLDBJ·TOCS·TACO·TALG·TOPLAS·JACM·SIAMCOMP·TPDS·TC·CSR) 2026년분 2,454편
+ OpenAlex API 2026 상반기 5개 subfield 6,236편. arXiv API는 429(rate limit)로 미사용.

### 105편 전수 감사 결과 (cutoff 2025-12-31, ○ = coverage ≥ 50% ∧ eligible ≥ 60 ∧ post-cutoff < 15%)

| 도메인 | 감사 | ○ | 통과 후보 (coverage / eligible) |
|---|---:|---:|---|
| ai | 8 | **8** | instruction-tuning 89/153 · function-calling 82/129 · model-merging 81/217 · diffusion-alignment 78/180 · agent-optimization 78/166 · rag-for-llms 77/135 · graph-rag 77/174 · dl-uncertainty 52/107 |
| db | 22 | **7** | retrieval-explainability 70/139 · trustworthy-rag 69/105 · large-models-timeseries 63/251 · diffusion-timeseries 63/183 · deep-graph-clustering 61/109 · negative-sampling-recsys 55/138 · llm-data-preparation 50/66 |
| security | 11 | **5** | mllm-adversarial 86/94 · training-data-detection 76/83 · physical-adversarial 75/165 · harmful-finetuning 68/165 · watermarking 65/68 |
| systems | 22 | **5** | moe-inference 77/161 · kv-cache 75/107 · **edge-slm-cloud-llm 73/198** · llm-edge-inference 69/113 · llm-dist-training 61/202 |
| algorithm | 8 | **3** | gnn-acceleration 70/122 · llm-algorithm-design 64/94 · graph-transformers 53/147 |
| network | 22 | **3** | edge-cloud 61/213 · wireless-foundation-models 60/170 · ai-wireless-reasoning 55/89 |
| se | 12 | **2** | prompt-code-summarization 68/65 · llm4se 57/67 |
| **합계** | **105** | **33** | |

D1(no_cs_topic 유실) 도메인별: ai 10.5% · algorithm 9.0% · db 6.3% · network **18.0%(임계 초과)** · se 7.0% · security 5.4% · systems 4.3%

### 8차가 확인한 것

1. **db 도메인 부활**: D6에서 본선 1편으로 보류했으나, IR·시계열·그래프 학습 축으로 재모집하니 ○7편. 보류 해제 가능.
2. **systems 5편 완성**: `edge-slm-cloud-llm`(CSUR, 73%/198)이 추가되어 도메인당 5편 요건 충족.
3. **algorithm 신설의 한계가 명확**: 8편 중 ○3이고, 전부 **ML/LLM 교차 주제**다. 순수 축은 전부 미달 —
   vector-commitment 0%(암호, IACR 생태) · out-of-core graph 26% · multi-fidelity optimization 23% ·
   quantum-optimization 22%. 진화연산·최적화 저널(IEEE TEVC 등) 정전이 arXiv에 없는 것이 원인으로,
   D5에서 관찰된 패턴이 algorithm에서도 그대로 재현됐다.
4. **추출 경로 한계 노출**: TKDE·VLDBJ·TOSEM 2026 신간 일부는 S2 미색인이라 Crossref fallback으로 빠졌고,
   기탁 ref에 arXiv id가 거의 없어 식별률 0~3%로 찍힌다(`dl-timeseries-forecasting` 1%,
   `dynamic-graph-processing` 0%, `mmkg-entity-alignment` 3%, `cloud-anomaly-monitoring` 1%).
   **이 수치는 문헌 생태가 아니라 측정 한계이므로 판정 근거로 쓰지 말고 S2 색인 후 재추출한다.**

### 미결

- [ ] `scripts/audit_candidates.py:144` coverage 분모에서 post-cutoff ref 제외 (문서 §0-3과 구현 불일치).
      영향 실측: `security/embodied-ai-safety` 36%→57%(elig 64) **△→○**, `harmful-finetuning` 68%→75%,
      나머지는 ±1.5%p 이내. `se/terminal-agents`는 20%→53%이나 게이트①(post-cutoff 44%) 탈락 유지.
- [ ] S2 색인 후 재추출: llm-agents-se · lm-compression · llm-watermarking · TKDE/VLDBJ 계열 4편
- [x] 최종 25편 확정 → `SELECTION.md` · `gt_exclude.txt`(15 id) — D9 (2026-09-02)
- [x] `create-view --name bench-2512` (947,451편) + `export-agent-db` 2종 — 2026-09-02, 상세는 SELECTION.md §5
- [ ] agent별 임베딩 빌드 → 4 agent 생성 실험 (docs/autosurvey-usage.md)
