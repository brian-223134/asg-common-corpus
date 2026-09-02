# Benchmark Topic 최종 선정표 (5 domains × 5 topics) — 확정 2026-09-02

**감사 모집단**: 후보 105편 전수 (`data/audit/candidates_report.json`) · **corpus cutoff**: 2025-12-31
**선정 도메인**: ai · db · security · systems · **network** · **보류**: algorithm · se (§4)

> **한 줄 요약**: survey topic을 먼저 정하지 않고, cutoff 이후 publish된 human survey를 먼저 찾아
> 그 reference가 Common Corpus에서 재현 가능한지를 자동 감사로 판정한 뒤,
> 통과한 survey의 주제를 benchmark topic으로 역산했다.

## 0. 선정 원칙 (결정 체인: docs/decisions.md D4~D9)

| 원칙 | 내용 | 근거 |
|---|---|---|
| GT-first | topic이 아니라 GT survey를 먼저 선정 | GT 없는 topic은 채점 불가 |
| 품질 = venue | 2026 신간은 citation 무정보 → CSUR·COMST·TOSEM·TKDE 등 peer-review 통과를 품질 신호로 | 연령 정규화도 1년 미만에선 노이즈 |
| 자동 게이트 | post-cutoff < 15% ∧ eligible coverage ≥ 50% ∧ eligible ≥ 60편, 재량 불개입 | "왜 이 25편인가"를 측정으로 닫음 |
| eligible 분모 | 평가 분모 = GT ref ∩ corpus ∩ cutoff. **corpus 수동 추가 금지** | D4·D7 |
| **easy case 회피** | 커버리지 최대화가 아니라 **검색 난이도 유지**가 기준 | D7 (지도교수) |
| 도메인 = 다양성 축 | "한 도메인만 보지 않았다"를 위한 축. topic이 AI를 다뤄도 문제가 그 도메인이면 무방 | D7-3 |
| 축 다양성 | 도메인 내 같은 축 2편 초과 금지 | systems 5편이 전부 LLM 효율이던 문제 |
| 쌍둥이 처리 | GT의 pre-cutoff arXiv 선행판은 view에서 제외 | 누수 차단 |

**easy case가 아님을 확인한 실측**: 선정 토픽의 후보 풀(GT ref가 속한 OpenAlex topic 기준) 대비
정답 비율 **0.07~0.76%** — 관련 논문 2.8만~10만편 중 정답 60~213편.
**AI 편중이 정답지 중복으로 이어지지 않음**: 25편 쌍별 GT ref 중복 최대 6.1%, 도메인 간 평균 1% 미만.

## 1. 최종 25편

cov = eligible coverage(= recall ceiling) · elig = eligible ref 수(채점 분모) · twin = 제외할 preprint 선행판

### ai (○8 중 5 선정)
| # | topic | GT id | cov | elig | post | twin |
|---|---|---|---:|---:|---:|---|
| 1 | Instruction Tuning for LLMs | 10.1145/3777411 | 89% | 153/172 | 0.5% | 2308.10792 |
| 2 | Function Calling in LLMs | 10.1145/3788284 | 82% | 129/157 | 0.0% | — |
| 3 | Model Merging | 10.1145/3787849 | 81% | 217/268 | 0.0% | 2408.07666 |
| 4 | Diffusion Model Alignment | 10.1145/3796982 | 78% | 180/230 | 0.0% | — |
| 5 | LLM-based Agents Optimization | 10.1145/3789261 | 78% | 166/212 | 0.0% | 2503.12434 |

예비: rag-for-llms 77%/135 · graph-rag 77%/174 · dl-uncertainty 52%/107

### db (○7 중 5 선정 — D6 보류 해제, D9)
| # | topic | GT id | cov | elig | post | twin |
|---|---|---|---:|---:|---:|---|
| 1 | Explainability of Text Processing and Retrieval | 10.1145/3801957 | 70% | 139/200 | 0.0% | 2212.07126 |
| 2 | Trustworthy Retrieval-Augmented Generation | 10.1145/3837074 | 69% | 105/152 | 2.3% | 2502.06872 |
| 3 | Large Models for Time Series & Spatio-Temporal Data | 10.1145/3821637 | 63% | 251/396 | 0.2% | 2310.10196 |
| 4 | Deep Graph Clustering | 10.1109/tkde.2026.3669747 | 61% | 109/180 | 0.0% | 2211.12875 |
| 5 | Negative Sampling in Recommendation | 10.1145/3793855 | 55% | 138/249 | 0.0% | — |

예비: diffusion-timeseries 63%/183 (시계열 축 중복으로 미채택) · llm-data-preparation 50%/66

### security (○ 정확히 5)
| # | topic | GT id | cov | elig | post | twin |
|---|---|---|---:|---:|---:|---|
| 1 | Adversarial Attacks on MLLMs | arXiv 2603.27918 | 86% | 94/109 | 0.0% | — |
| 2 | LLM Training-Data Detection | 10.1145/3779430 | 76% | 83/109 | 0.0% | — |
| 3 | Physical-World Adversarial Attacks | 10.1145/3793659 | 75% | 165/220 | 0.0% | 2211.01671 |
| 4 | Harmful Fine-tuning Attacks/Defenses | 10.1145/3817114 | 68% | 165/241 | 8.4% | 2409.18169 |
| 5 | LLM Watermarking/Fingerprinting | 10.1145/3773028 | 65% | 68/105 | 0.0% | — |

예비: embodied-ai-safety (분모 수정 시 57%/64 — §5 미결) · tinyml-security 57%/55

### systems (○ 정확히 5 — 8차로 완성)
| # | topic | GT id | cov | elig | post | twin |
|---|---|---|---:|---:|---:|---|
| 1 | MoE Inference Optimization | 10.1145/3794845 | 77% | 161/208 | 0.8% | 2412.14219 |
| 2 | KV Cache Optimization for LLM Serving | 10.18653/v1/2026.findings-acl.1916 | 75% | 107/142 | 2.7% | — |
| 3 | Edge SLM ↔ Cloud LLM Collaborative Inference | 10.1145/3838593 | 73% | 198/272 | 1.4% | — |
| 4 | LLM Edge Inference | 10.1145/3809166 | 69% | 113/164 | 1.0% | — |
| 5 | LLM Distributed Training Infrastructure | 10.1007/s44336-026-00038-z | 61% | 202/330 | 0.0% | 2407.20018 |

⚠ **축 다양성 미충족 — 한계로 기록한다.** 5편이 전부 "LLM 추론/학습 효율" 축이다.
비-LLM 축은 8차 광역 모집에서도 전부 미달했다: SSD wear leveling · HPC I/O ML · GPU 가속(4%) ·
마이크로서비스 시뮬레이션/이상탐지(1%) · confidential computing(30%/44) · serverless(26~29%).
대체 후보가 존재하지 않으므로 선정이 아니라 corpus universe의 제약이다.

### network (○3 + eligible≥60 △2 — 5번째 도메인, D9)
| # | topic | GT id | cov | elig | post | twin |
|---|---|---|---:|---:|---:|---|
| 1 | Edge-Cloud Collaborative Computing | 10.1109/comst.2026.3669216 | 61% | 213/350 | 0.0% | 2505.01821 |
| 2 | Multi-Modal Foundation Models for Wireless Networks | arXiv 2601.03181 | 60% | 170/285 | 0.0% | — |
| 3 | AI Reasoning for Wireless Communications | 10.1145/3811822 | 55% | 89/163 | 2.5% | — |
| 4 | Agentic Satellite-Terrestrial Networks | 10.1109/comst.2026.3660854 | **25%** | 80/315 | 2.4% | — |
| 5 | AI-Assisted Adaptive Video Streaming | 10.1145/3838182 | **26%** | 64/243 | 4.5% | 2406.02302 |

예비: ml-open-ran 23%/63 · genai-for-iot 37%/51
⚠ 4·5번은 ceiling이 25~26%로 낮다. eligible 절대수(80·64편)는 충족하나 **점수 상한이 낮아
agent 간 변별력이 압축**되므로 결과표에 ceiling을 반드시 병기한다.

## 2. 난이도 공변량 (결과 해석용, 결과표에 병기)

| 축 | 범위 | 비고 |
|---|---|---|
| recall ceiling (cov) | 25~89% | topic별 최대 달성 가능 점수 |
| eligible ref 수 | 64~251편 | 채점 분모, 전 topic ≥ 60 충족 |
| 후보 풀 대비 정답 비율 | 0.07~0.76% | easy case 아님의 근거 (D7) |
| post-cutoff ref 비율 | 0.0~8.4% | 전 topic 게이트(15%) 통과 |
| GT ref median 연도 | 2020~2024 | 2020년 이후 비율 53~98% — T_model 오염 가능성(한계) |

## 3. 누수 차단 — `candidates/gt_exclude.txt` (15개 arXiv id)

| 구분 | id |
|---|---|
| GT 본체가 arXiv (cutoff로도 걸러지나 이중 게이트) | 2601.03181 (wireless-foundation-models) · 2603.27918 (mllm-adversarial-attacks) |
| preprint 쌍둥이 13건 | 2211.01671 · 2211.12875 · 2212.07126 · 2308.10792 · 2310.10196 · 2406.02302 · 2407.20018 · 2408.07666 · 2409.18169 · 2412.14219 · 2502.06872 · 2503.12434 · 2505.01821 |

`--exclude-file`은 주석 줄을 걸러내지 않으므로 파일에는 **id만** 둔다(출처 매핑은 이 표가 정본).

## 4. 보류 도메인 (데이터 전량 보존)

### algorithm — 보류 (8차 신설, 감사 8편 · ○3)
5편 구성이 불가능해 보류한다. eligible ≥ 60편인 후보가 4편뿐이고(5번째 `out-of-core-graph-processing`은
31편), ○3편 중 2편(gnn-acceleration · graph-transformers)이 그래프 학습 축이라 축 다양성 제약에도 걸린다.
- ○: gnn-acceleration 70%/122 · llm-algorithm-design 64%/94 · graph-transformers 53%/147
- 미달: multi-fidelity-optimization 23%/70 · out-of-core-graph 26%/31 · llm-combinatorial-opt 24%/16 ·
  quantum-optimization-se 22%/35 · **vector-commitment 0%** (IACR ePrint 생태, 암호 probe 4~7%와 일치)
- **재개 조건**: 그래프 학습이 아닌 축(예: 학습된 인덱스/자료구조, 스트리밍·근사 알고리즘, 분산 합의)에서
  eligible ≥ 60편 후보 2편 추가 확보. 다만 순수 이론 축은 진화연산·최적화 저널(IEEE TEVC 등) 정전이
  arXiv에 없어 20%대에 머무는 것이 8차에서 확인됐다.

### se — 보류 (감사 12편 · ○2)
- ○: prompt-code-summarization 68%/65 · llm4se 57%/67
- △: code-intelligence-context 50%/111 · software-defect-datasets 31%/68 · llm-agents-se 29%*/66 (*Crossref 하한)
- **원인**: corpus의 Software subfield가 4K~13K편으로 가장 얇고, SE survey는 ICSE/FSE 정전을 인용한다.
- **재개 조건**: llm-agents-se·lm-compression의 S2 색인 후 재추출로 하한이 해소되면 ○4까지 가능.

두 도메인 모두 `candidates/<domain>/` 아래 candidate.yaml·refs.json과 감사 결과를 **삭제하지 않는다**
(탈락 사유가 곧 벤치마크 문서의 근거 — README §6).

## 5. 후속 절차와 미결

```bash
PY=/data2/chanjoong/miniforge3/envs/asg-corpus/bin/python
$PY -m common_corpus.cli create-view --name bench-2512 \
    --cutoff 2025-12-31 --exclude-file candidates/gt_exclude.txt
$PY -m common_corpus.cli export-agent-db --view bench-2512 --format autosurvey
$PY -m common_corpus.cli export-agent-db --view bench-2512 --format surveyforge
```

- [ ] `scripts/audit_candidates.py:144` coverage 분모에서 post-cutoff ref 제외 (설계 문서 §0-3과 구현 불일치).
      실측 영향: `security/embodied-ai-safety` 36%→57%(elig 64) △→○ · `harmful-finetuning` 68%→75% ·
      나머지 ±1.5%p 이내. 수정 시 security 예비 후보가 하나 늘어난다.
- [ ] S2 색인 후 재추출: llm-agents-se · lm-compression · llm-watermarking · TKDE/VLDBJ/TOSEM 계열 4편
      (`dl-timeseries-forecasting` 1% · `dynamic-graph-processing` 0% · `mmkg-entity-alignment` 3% ·
      `cloud-anomaly-monitoring` 1% — 문헌 생태가 아니라 Crossref fallback의 측정 한계)
- [ ] 결과 보고 시 topic별 recall ceiling·후보 풀 크기 병기, systems 축 편중과 T_model 오염을 한계로 기술
