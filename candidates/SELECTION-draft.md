# Topic 선정표 초안 (5 domains × 5) — 2026-09-01, 71편 감사 기준

도메인 구성(D6): **ai · se · security · systems · network** (db는 선정 보류, 데이터 보존)

기준(D5): 본선 coverage ≥50% ∧ eligible ≥60 (○), 한계 eligible ≥40 (△). cutoff 2025-12-31.
수치: eligible/식별 (coverage). twin = corpus 내 preprint 쌍둥이 → **최종 view exclude 목록에 GT와 함께 등록**.

## ai — 확정 가능 (○ 8편 중 5)
| # | topic | 수치 | twin |
|---|---|---|---|
| 1 | instruction-tuning-llms | 153/172 (89%) | 2308.10792 |
| 2 | llm-function-calling | 129/157 (82%) | — |
| 3 | model-merging | 217/268 (81%) | 2408.07666 |
| 4 | diffusion-model-alignment | 180/230 (78%) | — |
| 5 | llm-agent-optimization | 166/212 (78%) | 2503.12434 |
| 예비 | graph-rag (77%), rag-for-llms (77%), dl-uncertainty (52%) | | |

## security — 확정 가능 (○ 정확히 5)
| # | topic | 수치 | twin |
|---|---|---|---|
| 1 | mllm-adversarial-attacks | 94/109 (86%) | — |
| 2 | llm-training-data-detection | 83/109 (76%) | — |
| 3 | physical-adversarial-attacks | 165/220 (75%) | 2211.01671 |
| 4 | harmful-finetuning | 165/241 (68%) | 2409.18169 |
| 5 | llm-watermarking | 68/105 (65%) | — |
| 예비 | tinyml-security (57%/55) · embodied-ai-safety (추출 미완, S2 429) | | |

## systems — 4 + 1 (D5 재정의로 성립)
| # | topic | 수치 | twin |
|---|---|---|---|
| 1 | moe-inference-optimization | 161/208 (77%) | 2412.14219 |
| 2 | kv-cache-serving | 107/142 (75%) | — |
| 3 | llm-edge-inference | 113/164 (69%) | — |
| 4 | llm-distributed-training | 202/330 (61%) | 2407.20018 |
| 5△ | lm-compression | 41/57 (72%, Crossref 하한) | 2401.15347 |
| 예비 | dnn-partitioning-edge (36%/46) | | |

## se — 4 + 1 (경계 후보 포함)
| # | topic | 수치 | 비고 |
|---|---|---|---|
| 1 | prompt-code-summarization | 65/95 (68%) | |
| 2 | llm4se | 67/117 (57%) | twin 2312.15223 |
| 3 | code-intelligence-context | 111/223 (50%) | 경계(49.8%) |
| 4△ | llm-agents-se | 66/225 (29%, Crossref 하한) | twin 2409.02977 — **S2 색인 후 재추출로 상향 기대** |
| 5△ | software-defect-datasets | 68/222 (31%) | |

## network — 2 + 3 (D6 신설. △ 3편 포함 구성)
| # | topic | 수치 | 비고 |
|---|---|---|---|
| 1 | edge-cloud-collaboration | 213/350 (61%) | COMST. twin 2505.01821 |
| 2 | ai-wireless-reasoning | 89/163 (55%) | CSUR |
| 3△ | ai-video-streaming | 64/243 (26%) | twin 2406.02302 |
| 4△ | genai-for-iot | 51/139 (37%) | twin 2504.07635 |
| 5△ | llm-wireless-management | 56/284 (20%) | COMST |
| 예비 | ai-sfc-deployment (40/28%) | | |

원인 구조: 타 도메인과 동일한 venue 축(IEEE 저널 정전 비-arXiv)이 지배적. 무선-PHY 계열은
분류축(no_cs — OpenAlex가 Engineering으로 분류)이 부차적으로 겹침. CS-측 edge/fog 시도
(task-offloading 8%, fog-edge 9%)도 IEEE venue 문제로 실패 — network는 △ 없이 5편 구성 불가.

## db — 선정 보류 (D6). 기록용
llm-data-preparation ○ (66/50%) · deep-entity-resolution △ (45/46%) · minimal-perfect-hashing △ (47/32%)
— 재개 시 text-to-SQL·vector DB 계열 보충 모집부터.

### (구) db 세부
| # | topic | 수치 | 비고 |
|---|---|---|---|
| 1 | llm-data-preparation | 66/131 (50%) | |
| 2△ | deep-entity-resolution | 45/97 (46%) | eligible 45 |
| 3△ | minimal-perfect-hashing | 47/148 (32%) | |
| — | (모집 대상) text-to-SQL·vector DB·RAG data management·LLM4DB 계열 2026 survey | | arXiv API 복구 후 |

## 미결
- [x] db → 보류, network 신설(D6) 완료. network는 △ 3편 포함 5편 구성
- [ ] llm-agents-se·lm-compression: S2 색인 후 재추출 (Crossref 하한 해소)
- [ ] embodied-ai-safety 추출 재시도 (S2 429 + arXiv API 503 동시 장애로 대기)
- [ ] 확정 시: 25편 GT id + twin arXiv id 전체 → `gt_exclude.txt` 생성 → `create-view --exclude-file`
