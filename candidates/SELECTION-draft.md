# Benchmark Topic 선정표 (5 domains × 5) — 2026-09-01, 79편 전수 감사 기준

> **세미나용 한 줄 요약**: survey topic을 먼저 정하지 않고, **cutoff(2025-12-31) 이후 publish된
> high-quality human survey를 먼저 찾아** 그 reference가 Common Corpus에서 재현 가능한지를
> **자동 감사로 판정**한 뒤, 통과한 survey의 주제를 benchmark topic으로 역산했다.

## 0. 선정 원칙 (결정 체인: docs/decisions.md D4~D6)

| 원칙 | 내용 | 근거 |
|---|---|---|
| GT-first | topic이 아니라 GT survey를 먼저 선정 | GT 없는 topic은 채점 불가 |
| 품질 = venue | 2026 신간은 citation 무정보 → CSUR·COMST·TOSEM 등 peer-review 통과를 품질 신호로 | 연령 정규화도 1년 미만에선 노이즈 |
| 자동 게이트 | post-cutoff<15% ∧ eligible coverage≥50% ∧ eligible≥60편, 재량 불개입 | "왜 이 25편인가"를 측정으로 닫음 |
| eligible 분모 | 평가 분모 = GT ref ∩ corpus ∩ cutoff. **corpus 수동 추가 금지** | universe 규칙성·누수 방지 (D4) |
| 도메인 = arXiv-활성 하위영역 | 정통 OS/DS·암호·전통 SE는 universe 밖으로 명시 | preprint 문화 시차 실측 (D5) |
| 쌍둥이 처리 | GT의 pre-cutoff arXiv 판은 view에서 제외, T_model 우려는 기록 | 누수 차단 |

**게이트가 거르는 것의 실측 예**: 8월 신간(post-cutoff 44%), 암호 survey(IACR 생태, 4~7%),
정통 systems(SOSP/OSDI 정전, 8~30%), 6G-PHY(IEEE 정전+Engineering 분류, 5~15%).

## 1. 도메인별 선정 (○=본선 기준 충족, △=eligible≥40 한계 후보)

### ai — ○ 8편 중 5 선정
| # | topic (GT) | eligible | cov | twin |
|---|---|---|---|---|
| 1 | Instruction Tuning for LLMs | 153/172 | 89% | 2308.10792 |
| 2 | Function Calling in LLMs | 129/157 | 82% | — |
| 3 | Model Merging | 217/268 | 81% | 2408.07666 |
| 4 | Diffusion Model Alignment | 180/230 | 78% | — |
| 5 | LLM-based Agents Optimization | 166/212 | 78% | 2503.12434 |
| 예비 | graph-rag 77% · rag-for-llms 77% · dl-uncertainty 52% | | | |

### security — ○ 정확히 5 (전부 ML-security)
| # | topic | eligible | cov | twin |
|---|---|---|---|---|
| 1 | Adversarial Attacks on MLLMs | 94/109 | 86% | — |
| 2 | LLM Training-Data Detection | 83/109 | 76% | — |
| 3 | Physical-World Adversarial Attacks | 165/220 | 75% | 2211.01671 |
| 4 | Harmful Fine-tuning Attacks/Defenses | 165/241 | 68% | 2409.18169 |
| 5 | LLM Watermarking/Fingerprinting | 68/105 | 65% | — |
| 예비 | tinyml-security 57%/55 · embodied-ai-safety(추출 보류) | | | |

### systems — ○ 4 + △ 1 (D5: ML 인프라로 정의)
| # | topic | eligible | cov | twin |
|---|---|---|---|---|
| 1 | MoE Inference Optimization | 161/208 | 77% | 2412.14219 |
| 2 | KV Cache Optimization for LLM Serving | 107/142 | 75% | — |
| 3 | LLM Edge Inference | 113/164 | 69% | — |
| 4 | LLM Distributed Training Infrastructure | 202/330 | 61% | 2407.20018 |
| 5△ | LM Compression | 41/57 | 72%* | 2401.15347 |
| 예비 | dnn-partitioning-edge 36%/46 | | *Crossref 하한 — S2 색인 후 재추출 예정 | |

### se — ○ 3 + △ 2 (code intelligence/LLM4SE로 정의)
| # | topic | eligible | cov | 비고 |
|---|---|---|---|---|
| 1 | Prompt-Driven Code Summarization | 65/95 | 68% | |
| 2 | LLMs for Software Engineering | 67/117 | 57% | twin 2312.15223 |
| 3 | Context Utilization in Code Intelligence | 111/223 | 50% | 경계 |
| 4△ | LLM-based Agents for SE (TOSEM) | 66/225 | 29%* | twin 2409.02977. *Crossref 하한 |
| 5△ | Software Defect Datasets | 68/222 | 31% | |

### network — ○ 3 + △ 2 (D6 신설: AI×networking 교차. 7차 광역 재발굴로 확충)
| # | topic | eligible | cov | twin |
|---|---|---|---|---|
| 1 | Edge-Cloud Collaborative Computing (COMST) | 213/350 | 61% | 2505.01821 |
| 2 | Wireless Foundation Models (arXiv 2601) | 170/285 | 60% | — |
| 3 | AI Reasoning for Wireless Networks (CSUR) | 89/163 | 55% | — |
| 4△ | Agentic Satellite-Terrestrial Networks (COMST) | 80/315 | 25% | — |
| 5△ | AI-Assisted Video Streaming (CSUR) | 64/243 | 26% | 2406.02302 |
| 예비 | genai-for-iot 37%/51 · ai-sfc 28%/40 · ml-open-ran 23%/63 | | | |

실측 패턴: 통신 코어(6G-PHY·semantic comm·computing power networks)에 가까울수록 5~15%,
AI 교차(edge-cloud·foundation model·agentic)일수록 55~61% — D5 원칙이 network에서도 재확인됨.

### (db — D6로 선정 보류, 데이터 보존)
llm-data-preparation ○(66/50%) · deep-entity-resolution △(45/46%) · minimal-perfect-hashing △(47/32%).
재개 시 text-to-SQL·vector DB 계열 보충 모집부터.

## 2. 확정 시 후속 절차

1. 25편 GT id(+ pre-cutoff twin arXiv id 전체) → `gt_exclude.txt`
2. `create-view --name bench-2512 --cutoff 2025-12-31 --exclude-file gt_exclude.txt`
3. `export-agent-db` → agent별 DB/입력 재빌드 → 4 agent 생성 실험
4. 결과 보고 시 topic별 **recall ceiling**(eligible coverage) 명시 — △ 후보는 특히

## 3. 미결
- [ ] △ 5편(se 2·systems 1·network 2)의 채택/교체 최종 확인 (사용자)
- [ ] llm-agents-se·lm-compression: S2 색인 후 재추출 (Crossref 하한 해소)
- [ ] embodied-ai-safety 추출 재시도
