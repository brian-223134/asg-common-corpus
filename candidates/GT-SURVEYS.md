# GT Survey 목록 — benchmark `bench-2512`

**확정 2026-09-02 (docs/decisions.md D9)** · 선정 근거와 전체 수치는 [SELECTION.md](SELECTION.md) ·
view 제외 목록은 [gt_exclude.txt](gt_exclude.txt) · 후보 감사 원본은 `data/audit/candidates_report.json`

이 25편이 벤치마크의 **정답지(Ground Truth)** 다. 4개 ASG agent(AutoSurvey · SurveyForge ·
SurveyX · LLM×MapReduce-V2)가 **Topic** 열의 문자열을 입력으로 받아 survey를 생성하고,
결과를 이 human survey와 비교해 채점한다.

| 열 | 의미 |
|---|---|
| **Topic** | agent에 그대로 넣는 입력 문자열 |
| **cov** | recall ceiling — GT 인용문헌 중 corpus에 있고 cutoff 이내인 비율. **agent 점수의 상한**이므로 결과표에 반드시 병기 |
| **elig** | 채점 분모가 되는 ref 수 (corpus 수록 ∧ cutoff 이내) |
| **twin** | 같은 survey의 arXiv 선행판. corpus에 있어 view에서 제외함(누수 차단) |

⚠ 25편 전부 corpus cutoff(**2025-12-31**) 이후 publish됐다 — GT 본체는 agent가 검색할 수 없다.


## AI (`ai`)

| # | Topic (agent 입력) | GT Survey | Venue | Published | 링크 | cov | elig | twin |
|---|---|---|---|---|---|---:|---:|---|
| 1 | Instruction Tuning for Large Language Models | Instruction Tuning for Large Language Models: A Survey | ACM CSUR | 2026-01-08 | [10.1145/3777411](https://doi.org/10.1145/3777411) | 89% | 153 | 2308.10792 |
| 2 | Function Calling in Large Language Models | Function Calling in Large Language Models: Industrial Practices, Challenges, and Future Directions | ACM CSUR | 2026-02-25 | [10.1145/3788284](https://doi.org/10.1145/3788284) | 82% | 129 | — |
| 3 | Model Merging in LLMs, MLLMs, and Beyond | Model Merging in LLMs, MLLMs, and Beyond: Methods, Theories, Applications and Opportunities | ACM CSUR | 2026-02-09 | [10.1145/3787849](https://doi.org/10.1145/3787849) | 81% | 217 | 2408.07666 |
| 4 | Alignment of Diffusion Models | Alignment of Diffusion Models: Fundamentals, Challenges, and Future | ACM CSUR | 2026-03-10 | [10.1145/3796982](https://doi.org/10.1145/3796982) | 78% | 180 | — |
| 5 | A Survey on the Optimization of Large Language Model-based Agents | A Survey on the Optimization of Large Language Model-based Agents | ACM CSUR | 2026-02-11 | [10.1145/3789261](https://doi.org/10.1145/3789261) | 78% | 166 | 2503.12434 |

## Database / Data-centric (`db`)

| # | Topic (agent 입력) | GT Survey | Venue | Published | 링크 | cov | elig | twin |
|---|---|---|---|---|---|---:|---:|---|
| 1 | Explainability of Text Processing and Retrieval Methods | Explainability of Text Processing and Retrieval Methods: A Survey | ACM CSUR | 2026-05-01 | [10.1145/3801957](https://doi.org/10.1145/3801957) | 70% | 139 | 2212.07126 |
| 2 | Trustworthy Retrieval-Augmented Generation | Towards Trustworthy Retrieval Augmented Generation for Large Language Models: A Survey | ACM CSUR | 2026-08-06 | [10.1145/3837074](https://doi.org/10.1145/3837074) | 69% | 105 | 2502.06872 |
| 3 | Large Models for Time Series and Spatio-Temporal Data | Large Models for Time Series and Spatio-Temporal Data: A Survey and Outlook | ACM CSUR | 2026-07-28 | [10.1145/3821637](https://doi.org/10.1145/3821637) | 63% | 251 | 2310.10196 |
| 4 | Deep Graph Clustering | A Survey of Deep Graph Clustering: Taxonomy, Challenge, Application, and Open Resource | IEEE TKDE | 2026-06-01 | [10.1109/tkde.2026.3669747](https://doi.org/10.1109/tkde.2026.3669747) | 61% | 109 | 2211.12875 |
| 5 | Negative Sampling in Recommendation | Negative Sampling in Recommendation | ACM TOIS | 2026-01-01 | [10.1145/3793855](https://doi.org/10.1145/3793855) | 55% | 138 | — |

## Security (`security`)

| # | Topic (agent 입력) | GT Survey | Venue | Published | 링크 | cov | elig | twin |
|---|---|---|---|---|---|---:|---:|---|
| 1 | Adversarial Attacks on Multimodal Large Language Models | Adversarial Attacks on Multimodal Large Language Models: A Comprehensive Survey | arXiv (preprint) | 2026-03-30 | [arXiv:2603.27918](https://arxiv.org/abs/2603.27918) | 86% | 94 | — |
| 2 | Detecting Training Data For Large Language Models | Detecting Training Data For Large Language Models: A Survey | ACM CSUR | 2026-02-12 | [10.1145/3779430](https://doi.org/10.1145/3779430) | 76% | 83 | — |
| 3 | Visual Adversarial Attacks and Defenses in the Physical World | Visual Adversarial Attacks and Defenses in the Physical World: A Survey | ACM CSUR | 2026-04-01 | [10.1145/3793659](https://doi.org/10.1145/3793659) | 75% | 165 | 2211.01671 |
| 4 | Harmful Fine-tuning Attacks and Defenses for Large Language Models | Harmful Fine-tuning Attacks and Defenses for Large Language Models: A Survey | ACM CSUR | 2026-06-23 | [10.1145/3817114](https://doi.org/10.1145/3817114) | 68% | 165 | 2409.18169 |
| 5 | Securing Large Language Models | Securing Large Language Models: A Survey of Watermarking and Fingerprinting Techniques | ACM CSUR | 2026-02-04 | [10.1145/3773028](https://doi.org/10.1145/3773028) | 65% | 68 | — |

## Systems (`systems`)

| # | Topic (agent 입력) | GT Survey | Venue | Published | 링크 | cov | elig | twin |
|---|---|---|---|---|---|---:|---:|---|
| 1 | A Survey on Inference Optimization Techniques for Mixture of Experts Models | A Survey on Inference Optimization Techniques for Mixture of Experts Models | ACM CSUR | 2026-03-09 | [10.1145/3794845](https://doi.org/10.1145/3794845) | 77% | 161 | 2412.14219 |
| 2 | Towards Efficient Large Language Model Serving | Towards Efficient Large Language Model Serving: A Survey on System-Aware KV Cache Optimization | ACL 2026 Findings | 2026-01-01 | [10.18653/v1/2026.findings-acl.1916](https://doi.org/10.18653/v1/2026.findings-acl.1916) | 75% | 107 | — |
| 3 | Collaborative Inference between Edge SLMs and Cloud LLMs | Collaborative Inference and Learning between Edge SLMs and Cloud LLMs: A Survey of Algorithms, Execution, and Open Challenges | ACM CSUR | 2026-08-24 | [10.1145/3838593](https://doi.org/10.1145/3838593) | 73% | 198 | — |
| 4 | Network Edge Inference for Large Language Models | Network Edge Inference for Large Language Models: Principles, Techniques, and Opportunities | ACM CSUR | 2026-05-19 | [10.1145/3809166](https://doi.org/10.1145/3809166) | 69% | 113 | — |
| 5 | Efficient training of large language models on distributed infrastructures | Efficient training of large language models on distributed infrastructures: a survey | Vicinagearth | 2026-06-01 | [10.1007/s44336-026-00038-z](https://doi.org/10.1007/s44336-026-00038-z) | 61% | 202 | 2407.20018 |

## Network (`network`)

| # | Topic (agent 입력) | GT Survey | Venue | Published | 링크 | cov | elig | twin |
|---|---|---|---|---|---|---:|---:|---|
| 1 | Edge-Cloud Collaborative Computing on Distributed Intelligence and Model Optimization | Edge-Cloud Collaborative Computing on Distributed Intelligence and Model Optimization: A Survey | IEEE COMST | 2026-01-01 | [10.1109/comst.2026.3669216](https://doi.org/10.1109/comst.2026.3669216) | 61% | 213 | 2505.01821 |
| 2 | Multi-Modal Data-Enhanced Foundation Models for Prediction and Control in Wireless Networks | Multi-Modal Data-Enhanced Foundation Models for Prediction and Control in Wireless Networks: A Survey | arXiv (preprint) | 2026-01-06 | [arXiv:2601.03181](https://arxiv.org/abs/2601.03181) | 60% | 170 | — |
| 3 | AI Reasoning for Wireless Communications and Networking | AI Reasoning for Wireless Communications and Networking: A Survey and Perspectives | ACM CSUR | 2026-06-24 | [10.1145/3811822](https://doi.org/10.1145/3811822) | 55% | 89 | — |
| 4 | Agentic Satellite-Augmented Low-Altitude Economy and Terrestrial Networks | Agentic Satellite-Augmented Low-Altitude Economy and Terrestrial Networks: A Survey | IEEE COMST | 2026-01-01 | [10.1109/comst.2026.3660854](https://doi.org/10.1109/comst.2026.3660854) | 25% | 80 | — |
| 5 | Towards AI-Assisted Sustainable Adaptive Video Streaming Systems | Towards AI-Assisted Sustainable Adaptive Video Streaming Systems: Tutorial and Survey | ACM CSUR | 2026-08-21 | [10.1145/3838182](https://doi.org/10.1145/3838182) | 26% | 64 | 2406.02302 |

## 슬러그 ↔ 디렉터리

각 GT의 등록 원본은 `candidates/<domain>/<slug>/`에 있다.

| domain | slug (순서는 위 표와 동일) |
|---|---|
| ai | `instruction-tuning-llms` · `llm-function-calling` · `model-merging` · `diffusion-model-alignment` · `llm-agent-optimization` |
| db | `retrieval-explainability` · `trustworthy-rag` · `large-models-timeseries` · `deep-graph-clustering` · `negative-sampling-recsys` |
| security | `mllm-adversarial-attacks` · `llm-training-data-detection` · `physical-adversarial-attacks` · `harmful-finetuning` · `llm-watermarking` |
| systems | `moe-inference-optimization` · `kv-cache-serving` · `edge-slm-cloud-llm` · `llm-edge-inference` · `llm-distributed-training` |
| network | `edge-cloud-collaboration` · `wireless-foundation-models` · `ai-wireless-reasoning` · `agentic-satellite-networks` · `ai-video-streaming` |

## 보류 도메인

`algorithm`(감사 8편 · ○3) · `se`(12편 · ○2)는 5편 구성이 불가능해 보류했다.
candidate.yaml · refs.json · 감사 결과는 전량 보존돼 있고, 재개 조건은
[SELECTION.md §4](SELECTION.md)에 기록돼 있다.

## 채점 시 사용법

- **reference 재현율**: 각 후보 디렉터리의 `refs.json`에 GT 인용문헌이 이미 추출돼 있다.
  GT 본문에 접근할 필요 없이 채점 가능하다.
  ```
  candidates/<domain>/<slug>/refs.json
    {"refs": [{"title", "arxiv_id", "doi", "publicationDate", "year"}, ...],
     "summary": {"refs", "arxiv_resolvable", "doi_only", "unresolved"},
     "source": "semanticscholar-graph-api" | "crossref-deposited" | "arxiv-eprint"}
  ```
  `source`가 `crossref-deposited`인 후보는 arXiv id 식별률이 낮아 수치가 하한이다
  (현 25편 중 llm-watermarking 1편 해당 — SELECTION.md §5 미결).
- **목차·내용 비교**: GT 본문이 필요하며 위 링크에서 받는다. ACM/IEEE는 기관 구독이 필요할 수 있다.
- **결과표**: topic별 `cov`(ceiling)를 반드시 병기한다. network 4·5번은 25~26%로 낮아
  agent 간 점수 차이가 압축된다.

