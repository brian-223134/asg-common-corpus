# LLM×MapReduce-V2에서 Common Corpus 사용하기 (2-stage 입력 빌더)

**대상 view**: `bench-2512` (947,451편) · GT 목록은 `candidates/GT-SURVEYS.md`

LLM×MapReduce-V2는 검색기가 아니라 **encode→map→reduce 파이프라인**이다. 입력이
"survey 1편 = topic + 참고문헌 pool(제목·초록·**전문**)"인 JSONL이므로, 공통 코퍼스는
**입력 JSONL을 만들어 주는 역할**을 한다. 파이프라인 자체는 손대지 않는다.

원 논문 설정대로 pool 구성에 AutoSurvey의 retrieval stack(nomic-embed + FAISS)을 그대로 쓴다 —
same-corpus 비교에서 **모든 agent가 하나의 retrieval 백엔드를 공유**하도록 하기 위함이다.

## 0. 선행 조건 — AutoSurvey DB가 먼저 있어야 한다

Stage 1이 AutoSurvey 포맷 DB(FAISS 인덱스 포함)를 읽는다. `docs/autosurvey-usage.md` §1을
먼저 수행해 `../AutoSurvey/database_commoncorpus-bench-2512/`를 만들어 둔다.
(같은 인덱스를 AutoSurvey 실행과 공유한다 — 중복 빌드 불필요)

## 1. Stage 1 — topic당 후보 pool retrieval (autosurvey env, GPU)

```bash
cd /data2/chanjoong/survey-agent/LLMxMapReduce-v2
CUDA_VISIBLE_DEVICES=<idle> /data2/chanjoong/miniforge3/envs/autosurvey/bin/python \
    scripts/retrieve_pool.py \
    --topics data/bench-2512/topics.jsonl \
    --db_path ../AutoSurvey/database_commoncorpus-bench-2512 \
    --exclude_file ../asg-common-corpus/candidates/gt_exclude.txt \
    --retrieve_num 1200 \
    --output data/pools/bench-2512.pools.jsonl
```

출력: topic당 한 줄 `{"title": ..., "arxiv_id_ranked": [...], "retrieve_num": N}`.
`--retrieve_num 1200`은 원 논문의 AutoSurvey식 pool 크기다.

`--topics`는 `{"title": ...}` per line JSONL이다. `candidates/GT-SURVEYS.md`의 **Topic** 열로
만들고, Stage 2의 `gt_count` 모드를 쓰려면 `n_gt_refs`(= 그 GT의 eligible 수)도 함께 넣는다.

## 2. Stage 2 — full text 확보 + 입력 JSONL (asg-corpus env)

```bash
/data2/chanjoong/miniforge3/envs/asg-corpus/bin/python scripts/build_corpus_input.py \
    --pools data/pools/bench-2512.pools.jsonl \
    --topics data/bench-2512/topics.jsonl \
    --view bench-2512 \
    --pool_mode gt_count \
    --output data/inputs/bench-2512.input.jsonl
```

pool 상위 논문의 전문을 FullTextResolver로 확보해(arXiv e-print → latex 파서 → 캐시 동결)
파이프라인이 기대하는 형식으로 쓴다:

```json
{"title": "<topic>", "papers": [{"title","abstract","url","txt","arxiv_id"}, ...]}
```

- `--pool_mode gt_count`가 기본이다 — survey당 pool 크기를 **그 GT의 참고문헌 수**에 맞춰
  원 논문 설정과 규모를 정합시킨다. 고정 크기가 필요하면 `--pool_mode fixed --pool_size N`.
- `--min_chars`(기본 2000) 미만으로 파싱된 논문은 제외된다.
- **첫 실행은 오래 걸린다** — arXiv fetch가 3초 politeness delay를 지키므로 topic 수 × pool 크기에
  비례한다(수 시간대). 캐시 후 재실행은 분 단위. 스모크는 `--limit_topics 1`.

## 3. Stage 3 — 파이프라인 실행 (llmxmr env)

생성된 `data/inputs/bench-2512.input.jsonl`을 EncodePipeline 입력으로 넣는다.
파이프라인 인자는 기존 실험과 동일하게 고정한다 (agent 고유 통제 변수).

## 4. 함정

- **env가 stage마다 다르다**: Stage 1은 `autosurvey`(faiss·sentence-transformers),
  Stage 2는 `asg-corpus`(common_corpus 패키지), Stage 3은 `llmxmr`. 섞으면 import 에러가 난다.
- **GT 제외를 두 곳에서 확인**: view에 이미 적용됐지만 Stage 1의 `--exclude_file`도 방어적으로
  넣는다. pool JSONL에 `gt_exclude.txt`의 id가 있으면 버그다.
- **전문 확보 실패는 정상 경로**: arXiv e-print가 PDF-only이거나 파싱이 실패하면 그 논문은
  pool에서 빠진다. 실패 건수를 실험 기록에 남길 것 — agent 간 조건 차이의 근거가 된다.
- **토큰량**: 원 논문 기준 survey당 24만~82만 토큰이다. 캐시 없이 반복 실행하지 말 것.

## 5. 재현성 기록

```
view = bench-2512
pools jsonl 경로 + retrieve_num
input jsonl 경로 + pool_mode
fulltext cache = data/fulltext_cache/arxiv/<id>/metadata.json 의 version+sha256
retrieval 백엔드 = ../AutoSurvey/database_commoncorpus-bench-2512 (manifest sha)
```

## 6. 참고

LLM×MapReduce-V2 쪽 상세 절차는 `../LLMxMapReduce-v2/docs/commoncorpus-setup.md`,
코퍼스 쪽 일반론은 `docs/integration-guide.md` §5-4.
