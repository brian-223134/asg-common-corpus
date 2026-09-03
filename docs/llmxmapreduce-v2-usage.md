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

⚠ **`check_db.py --verify-embeddings`의 오탐에 속지 말 것.** `bench-2512` DB는 이 검사에서
"문제 있음"으로 나오지만 **인덱스는 정상**이다. nomic-bert의 위치 캐시가 stateful이라
947K편 빌드 시점의 모델 상태와 갓 로딩한 모델로 1건 인코딩한 결과가 미세하게 달라
abs에서 cos≈0.985가 나온다(임계 0.999). 재빌드해도 같은 수치가 나온다.

**진짜 고장과 구분하는 지표**: 순서·매핑이 깨졌다면 argmax 자기일치가 무너진다.
실측은 argmax 자기일치 12/12 · 비대각 최대 0.71 · title은 정확히 1.0 — 정상이다.
이 경고만으로 1시간 18분짜리 재빌드를 다시 돌리지 말 것.

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

### `topics.jsonl`을 먼저 만들어야 한다 — 저장소에 없다

`--topics`가 가리키는 파일은 **직접 생성한다.** 두 필드가 정본에서 온다:

| 필드 | 출처 |
|---|---|
| `title` | `candidates/GT-SURVEYS.md`의 **Topic** 열 (agent 입력 문자열의 정본) |
| `n_gt_refs` | 같은 표의 **elig** 열 — **`cov`가 아니라 `elig`다** (채점 분모가 되는 ref 수) |

`--pool_mode gt_count`(기본값)가 `n_gt_refs`를 필수로 읽고, 없으면
`KeyError: topic ... not in ...`으로 죽는다(`build_corpus_input.py:88-89`).

25편 전체를 GT-SURVEYS.md에서 뽑는 스니펫:

```bash
cd /data2/chanjoong/survey-agent/LLMxMapReduce-v2
mkdir -p data/bench-2512
python3 - <<'EOF' > data/bench-2512/topics.jsonl
import io, json, re
GT = '../asg-common-corpus/candidates/GT-SURVEYS.md'
dom = None
for ln in io.open(GT, encoding='utf-8'):
    h = re.match(r'^## .*\(`(\w+)`\)', ln)
    if h:
        dom = h.group(1); continue
    c = [x.strip() for x in ln.strip().strip('|').split('|')]
    if dom and len(c) == 9 and c[0].isdigit():          # 도메인 표의 데이터 행만
        print(json.dumps({"title": c[1], "n_gt_refs": int(c[7]),
                          "domain": dom, "gt": re.sub(r'.*\[(.*?)\].*', r'\1', c[5])},
                         ensure_ascii=False))
EOF
wc -l data/bench-2512/topics.jsonl        # 25 이어야 한다
```

출력 예: `{"title": "Instruction Tuning for Large Language Models", "n_gt_refs": 153,
"domain": "ai", "gt": "10.1145/3777411"}`

**GT-SURVEYS.md의 표 구조가 바뀌면 이 스니펫도 깨진다** — `wc -l`이 25가 아니면 멈출 것.

## 2. Stage 2 — full text 확보 + 입력 JSONL (asg-corpus env)

```bash
/data2/chanjoong/miniforge3/envs/asg-corpus/bin/python scripts/build_corpus_input.py \
    --pools data/pools/bench-2512.pools.jsonl \
    --topics data/bench-2512/topics.jsonl \
    --view bench-2512 \
    --pool_mode gt_count \
    --fetch_delay 4 \
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
- `--fetch_delay`(기본 3.0초)는 arXiv politeness delay다. **429가 뜨면 올린다** — 아래 실측은
  4초 기준이다.

**소요 시간 실측** (2026-09-03, topic 1편 · pool 153편):

| 단계 | 실측 |
|---|---|
| Stage 1 retrieval | 약 1분 (대부분 DB·FAISS 로딩) |
| Stage 2 full text | **11.7분** (154편 순회, 신규 fetch ~100편, `--fetch_delay 4`) |
| 확보율 | 153/154 (실패 1건 = 정당한 404) |
| 처리율 | 약 8.4편/분 |

25 topic 환산은 캐시 미적중 기준 **4~5시간**이다. provider가 논문당 2요청(버전 조회 API +
e-print)에서 **1요청**(버전 없는 e-print + content-disposition에서 버전 회수)으로 바뀌어
이전 추정의 절반이 됐다. 캐시 후 재실행은 분 단위. 스모크는 `--limit_topics 1`.

## 3. Stage 3 — 파이프라인 실행 (llmxmr env)

```bash
cd /data2/chanjoong/survey-agent/LLMxMapReduce-v2/LLMxMapReduce_V2
set -a && . ../.env && set +a          # 필수 — 아래 참조
PYTHONPATH=$(pwd) <llmxmr python> ./src/start_pipeline.py \
    --input_file ../data/inputs/bench-2512.input.jsonl \
    --output_file ./output/bench-2512.llama33-70b.jsonl \
    --config_file ./config/model_config_llama.json \
    --data_num <topic 수> --parallel_num 4
```

⚠ **`.env` 선행 로드가 필수다** — `OPENAI_API_KEY` · `LLMXMR_PROVIDER` ·
`LLMXMR_TEMPERATURE` · `NLTK_DATA`를 파이프라인이 환경에서 읽는다. `set -a`로 export
속성을 켜고 source해야 자식 프로세스까지 전달된다.

파이프라인 인자는 기존 실험과 동일하게 고정한다 (agent 고유 통제 변수).

## 4. 함정

- **env가 stage마다 다르다**: Stage 1은 `autosurvey`(faiss·sentence-transformers),
  Stage 2는 `asg-corpus`(common_corpus 패키지), Stage 3은 `llmxmr`. 섞으면 import 에러가 난다.
- **GT 제외를 두 곳에서 확인**: view에 이미 적용됐지만 Stage 1의 `--exclude_file`도 방어적으로
  넣는다. pool JSONL에 `gt_exclude.txt`의 id가 있으면 버그다.
- **전문 확보 실패는 정상 경로**: arXiv e-print가 PDF-only이거나 파싱이 실패하면 그 논문은
  pool에서 빠진다. 실패 건수를 실험 기록에 남길 것 — agent 간 조건 차이의 근거가 된다.
- **arXiv 429와 실패 캐시**: `failure.json`은 **공유 캐시**라 한 번 동결되면 이후 모든 실행·
  모든 agent에서 그 논문이 pool 밖으로 빠진다. 일시적 오류까지 동결되면 arXiv가 잠깐
  막았다는 이유만으로 pool 구성이 문헌이 아니라 **실행 시점**에 좌우된다.
  → 커밋 `6eccd7d` 이후 **429·타임아웃·URLError는 동결하지 않는다**(지수 백오프로 최대 4회
  재시도 후 그대로 raise, 빈 슬롯만 남아 다음 실행이 곧 재시도다). `failure.json`에 남는 것은
  404·파싱 실패·본문 500자 미만 같은 **영구 오류뿐**이다.
  실행 후 감사는 여전히 하되, 이제는 **오염 제거가 아니라 기록 목적**이다:
  ```bash
  cd ../asg-common-corpus/data/fulltext_cache/arxiv
  cat */failure.json | grep -o '"error": "[^"]*"' | sort | uniq -c | sort -rn
  ```
  429/timeout/URLError가 보이면 `6eccd7d` 이전에 만들어진 잔재이므로 해당 슬롯을 지우고
  재실행한다. (2026-09-03 기준 캐시 551슬롯 중 동결 4건 — 404 2 · 파싱 실패 2, 일시적 오류 0)
- **중단할 때는 python 프로세스를 죽인다**: `kill <nohup 래퍼 pid>`로는 자식 python이 살아남아
  계속 arXiv를 때린다. `pkill -f build_corpus_input.py`로 확인 사살할 것.
- **토큰량**: 원 논문 기준 survey당 24만~82만 토큰이다. 캐시 없이 반복 실행하지 말 것.

## 5. 재현성 기록

```
view = bench-2512
pools jsonl 경로 + retrieve_num
input jsonl 경로 + pool_mode + fetch_delay        # pool 구성 재현에 영향
fulltext cache = data/fulltext_cache/arxiv/<id>/metadata.json 의 version+sha256
fulltext resolver/provider 커밋 해시               # 재시도·동결 정책이 pool 구성을 바꾼다
failure.json 감사 결과 (동결된 id와 사유)
retrieval 백엔드 = ../AutoSurvey/database_commoncorpus-bench-2512 (manifest sha)
```

`fetch_delay`와 resolver 커밋을 남기는 이유: 같은 view·같은 pools에서도 전문 확보에 실패한
논문이 pool에서 빠지므로, **재시도 정책이 곧 pool 구성**이다. `build_corpus_input.py`가
run manifest에 `fetch_delay`를 이미 기록하므로 그 값을 인용하면 된다.

## 6. 참고

LLM×MapReduce-V2 쪽 상세 절차는 `../LLMxMapReduce-v2/docs/commoncorpus-setup.md`,
코퍼스 쪽 일반론은 `docs/integration-guide.md` §5-4.
