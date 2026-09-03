# SurveyForge에서 Common Corpus 사용하기 (경로 B — agent 코드 수정 0줄)

**대상 view**: `bench-2512` (benchmark 확정본, 947,451편) · GT 목록은 `candidates/GT-SURVEYS.md`
**결정 배경**: survey-search 경유(경로 A)는 쓰지 않는다(docs/decisions.md D3).
SurveyForge의 기존 DB 포맷을 Common Corpus에서 그대로 생성하고 `--db_path`만 바꾼다.

## 0. 준비된 입력

| 파일 | 내용 |
|---|---|
| `data/exports/bench-2512.surveyforge.json` | **947,451편**, TinyDB `{"cs_paper_info": {...}}`, 필드 `id,title,url,date,abs,cat,citation_count` (1.23GB) |
| 같은 경로 `.manifest.json` | `content_sha256` + view→corpus→upstream sha 체인 (실험 기록에 인용) |

다른 cutoff/GT로 새 view가 필요하면:
```bash
cd /data2/chanjoong/survey-agent/asg-common-corpus
PY=/data2/chanjoong/miniforge3/envs/asg-corpus/bin/python
$PY -m common_corpus.cli create-view --name <실험명> --cutoff <YYYY-MM-DD> \
    --exclude-file candidates/gt_exclude.txt
$PY -m common_corpus.cli export-agent-db --view <실험명> --format surveyforge
```

## 1. 논문 DB 스냅샷 + 임베딩 빌드 (1회, GPU)

SurveyForge 쪽에 이미 전용 빌더가 있다: `scripts/build_db_from_corpus.py`.
export JSON을 **바이트 그대로** 복사하고 gte-large 임베딩과 FAISS 인덱스를 만든다.

```bash
cd /data2/chanjoong/survey-agent/SurveyForge
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader   # 유휴 GPU 확인

CUDA_VISIBLE_DEVICES=<idle> \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
.venv/bin/python scripts/build_db_from_corpus.py \
    --export ../asg-common-corpus/data/exports/bench-2512.surveyforge.json \
    --out $SURVEYFORGE_DATA/database_cc-bench-2512 \
    --batch-size 8            # ⚠ 기본값 16은 OOM — 아래 "배치 크기" 참조
```

- **스모크**: `--limit 2000 --skip-survey-assets --out <scratch> --embedding-model $SURVEYFORGE_DATA/gte-large-en-v1.5`
  `--embedding-model` 기본값이 `<out의 부모 디렉터리>/gte-large-en-v1.5`라서(`build_db_from_corpus.py:129`),
  `--out`을 scratch로 보내면 `ValueError: Path .../scratchpad/gte-large-en-v1.5 not found`로 죽는다.
  본 빌드는 `--out`이 `$SURVEYFORGE_DATA` 아래라 기본값으로 동작한다.
- **검증**: `CUDA_VISIBLE_DEVICES=<idle> scripts/check_db.py --db <out> --verify-embeddings 20`
  `--verify-embeddings`는 재인코딩 대조라 GPU를 쓴다(`check_db.py:113-114`).

빌더가 지키는 불변식(해당 스크립트 헤더에 실측으로 문서화됨):
```
TinyDB 키 == arxivid_to_index_abs.json 값 == IndexIDMap stored id (1-based 연속)
faiss_paper_title_abs_* = encode(title + abs)   # 구분자 없는 단순 연결
faiss_paper_title_*     = encode(title)
IndexIDMap(IndexFlatIP), 1024-dim, L2 정규화, instruction prefix 없음
```
임베딩은 청크(기본 25,600편) 단위 체크포인트라 중단 후 **같은 명령으로 재시작 가능**하다 —
OOM으로 죽어도 처음부터 다시 하지 않는다.

### ⚠ 배치 크기 — 기본값 16은 OOM으로 죽는다 (2026-09-03 실측)

L40S(44.5 GiB)에서 기본 `--batch-size 16`이 **3분 만에** 터졌다:

```
torch.cuda.OutOfMemoryError: Tried to allocate 17.13 GiB.
GPU has 44.52 GiB total, 7.77 GiB free; 20.35 GiB allocated, 15.89 GiB reserved but unallocated
```

원인은 **corpus의 장문 초록 소수 + 원본 순서 배치**다. 빌더는 `title + abs`를 인코딩하는데,
배치를 원본 순서대로 자르므로 장문 레코드 하나가 배치 전체를 자기 길이로 패딩시킨다.
`16 batch × 16 head × 4,243 token² × 4B ≈ 17.1 GiB`로 에러 메시지의 요청량과 일치한다.

`title + abs` 길이 분포 (bench-2512 947,451편, corpus parquet 실측):

| p50 | p99 | p99.9 | 최대 | 10,000자 초과 |
|---:|---:|---:|---:|---:|
| 1,118자 | 2,005자 | 3,211자 | 10,131자 (`2107.02768`) | **24편** |

10,000자 초과 24편은 전부 **corpus의 abstract 10,000자 상한에 걸린 레코드**다. 평상시에는
안 걸리고 이 24편이 든 배치에서만 터지므로, 몇 시간 진행된 뒤에 죽을 수 있다.

**batch 8이 손해가 아니다 — 처리량이 오히려 높다:**

| 설정 | 처리량 | 결과 |
|---|---|---|
| batch 64 | — | OOM (surveyeval 빌드 이력) |
| batch 16 (기본값) | 82~93편/s | **OOM** (bench-2512, 3분) |
| **batch 8 + `expandable_segments:True`** | **103~108편/s** | 정상, ETA 2.3h |

GPU 메모리도 38.5 GiB → 21.1 GiB로 떨어진다(단편화 해소).

## 2. ⚠ Outline DB는 별도로 GT를 제외해야 한다

SurveyForge는 논문 DB 외에 **Survey Outline DB**(`surveys_arxiv_paper_db.json`, **18,816편**)를 쓴다.
이 DB는 **공통 corpus 범위 밖**이라 view의 GT 제외가 적용되지 않는다 — 벤치마크 GT survey가
아웃라인 예시로 검색될 수 있다.

**실측 (2026-09-03)**: `gt_exclude.txt` 15개 중 **7편이 outline DB에 실재**한다.

```
2211.01671v5  2211.12875v4  2212.07126v1  2308.10792v5
2310.10196v2  2406.02302v1  2407.20018v1
```

`code/src/database.py`가 환경변수로 거르는 경로를 제공한다. 매칭은 base id 기준이다
(`database.py:154`가 `i.split('v')[0]`으로 비교하므로 위처럼 버전 접미사가 붙어 있어도 걸린다).

⚠ **덮어쓰지 말고 합집합으로 쓸 것.** SurveyForge `.env`에는 **SurveyBench GT 20편**이 상시
켜져 있다. `gt_exclude.txt`의 15개로 덮으면 SurveyBench 실험 쪽이 깨진다. 두 목록은 겹치지 않으므로
**합집합 35개**가 정답이다. 과다 제외는 무해하다 — `database.py:153`이 `num + len(exclude)`만큼
더 뽑아 거른 뒤 `num`으로 자르므로 검색 결과 수가 줄지 않는다.

설정 위치는 `SurveyForge/.env`의 `SURVEYFORGE_SURVEY_EXCLUDE_IDS` 한 줄이며, **35개 합집합이
이미 적용돼 있다**(2026-09-03 확인). 검증:

```bash
# 35개인지, 두 목록을 모두 포함하는지 확인
grep '^SURVEYFORGE_SURVEY_EXCLUDE_IDS=' ../SurveyForge/.env | cut -d= -f2 | tr ',' '\n' | wc -l
```

**이 단계를 빠뜨리면 outline 단계에서 정답이 새어 실험이 무효가 된다.**

## 3. 실행

### 3.1 ⚠ 세 개의 시간 게이트를 먼저 푼다 — 안 풀면 2025년분이 통째로 사라진다

`main.py`는 view와 **별개로** 자체 시간 게이트 3개를 갖고 있고, **기본값이 전부 corpus보다 좁다.**
가장 위험한 건 날짜가 아니라 **id 게이트**다:

| 인자 (환경변수) | 기본값 | 그대로 두면 |
|---|---|---|
| `--paper_id_cutoff` (`SURVEYFORGE_PAPER_ID_CUTOFF`) | **`2412`** | **arXiv id `2501.*` 이상 전부 검색 불가 — 2025년분 전체** |
| `--paper_date_oldest` (`SURVEYFORGE_PAPER_DATE_OLDEST`) | `2012-01-01` | 1991~2011년분 리랭커에서 탈락 |
| `--paper_date_newest` (`SURVEYFORGE_PAPER_DATE_NEWEST`) | `2024-09-26` | 2024-09-27 이후 탈락 |

id 게이트는 **아웃라인·집필 양쪽**에 걸린다(`main.py:158`, `outline_writer.py:51`). 그리고
**끌 수 없다** — `main.py:176`의 `validate_cutoffs()`가 4자리 YYMM이 아니면 `SystemExit`한다.
따라서 DB 최댓값보다 큰 값을 줘서 **무효화**한다.

`.env`에 설정할 값 (이미 적용돼 있다, 2026-09-03 확인):

```bash
SURVEYFORGE_PAPER_ID_CUTOFF=2612      # 게이트를 끌 수 없으므로 DB 최대치(2512)보다 큰 값으로 무효화
SURVEYFORGE_PAPER_DATE_OLDEST=1991-01-01
SURVEYFORGE_PAPER_DATE_NEWEST=2026-01-01
```

- **구식 id는 안전하다.** `cs/0503039` 형식 54,217편은 전부 2007-04 이전이라 게이트를 그냥 통과한다
  (`utils.py`의 `arxiv_month()`가 구식 id를 실제 (연,월)로 변환해 9107~0703 wrap을 바르게 처리한다).
- **`paper_date_newest`는 `2025-12-31`도 정상 동작한다.** `utils.py:134-154`의 `get_time_windows`가
  `[oldest, newest]` **양끝 포함**이기 때문. 다만 SurveyForge 운용값은 `2026-01-01`(최대일+1)이고
  Edge Computing 파일럿에서 `[cutoff/rerank] total: 0/5,175 discarded`로 실증됐으므로,
  혼선을 줄이려 **`2026-01-01`로 통일**한다. 둘 다 정합이라 어느 쪽을 써도 결과는 같다.
- 실행 로그의 `[cutoff/cfg]` · `[cutoff/rerank]` 라인으로 실제 적용값과 탈락 편수를 확인할 것.

### 3.2 실행 — 교체 지점은 `.env`의 `SURVEYFORGE_DB_DIR` 한 줄

운용 진입점은 `code/run_demo.py`다. 이쪽이 `.env`의 `SURVEYFORGE_DATA` + `SURVEYFORGE_DB_DIR`을
읽어 `--db_path`를 조립하므로(`run_demo.py:100`), **바꾸는 것은 인자가 아니라 `.env` 한 줄**이다.

```bash
# SurveyForge/.env
SURVEYFORGE_DATA=/data2/chanjoong/survey-agent/SurveyForge_data
SURVEYFORGE_DB_DIR=database_cc-bench-2512      # ← 여기만 교체
```

```bash
cd /data2/chanjoong/survey-agent/SurveyForge/code
python run_demo.py --topic "<GT-SURVEYS.md의 Topic 열>"
```

`--embedding_model`도 `run_demo.py`가 `$SURVEYFORGE_DATA/gte-large-en-v1.5`로 넣어준다 —
인덱스를 만든 모델과 **반드시 동일**해야 하므로 손대지 않는다.

<details><summary>저수준 경로 — <code>main.py</code> 직접 호출</summary>

```bash
cd /data2/chanjoong/survey-agent/SurveyForge/code
python main.py --topic "<GT-SURVEYS.md의 Topic 열>" \
    --db_path $SURVEYFORGE_DATA/database_cc-bench-2512 \
    --embedding_model $SURVEYFORGE_DATA/gte-large-en-v1.5 \
    --paper_id_cutoff 2612 --paper_date_oldest 1991-01-01 --paper_date_newest 2026-01-01 \
    ...   # 나머지 인자는 run_demo.py의 목록과 동일하게 고정
```

`run_demo.py`가 넘기는 나머지 인자(`--section_num 7 --subsection_len 500 --rag_num 100
--rag_max_out 60 --outline_reference_num 1500` 등)를 빠뜨리면 기존 실험과 조건이 달라진다.
</details>

- 논문 DB 쪽 GT 제외는 view에서 끝났다. outline DB만 §2로 처리한다.

## 4. 알아둘 차이점

| 항목 | 기존 스냅샷 | Common Corpus DB |
|---|---|---|
| `id` | `1811.06122v1` (버전 접미사) | **`1811.06122` (base id)** — 불투명 키라 런타임 무해, 교차 비교는 base id로 |
| `date` | arXiv 수집 날짜 | `first_public_date` (day 53% / month 47%, month는 월초) |
| `cat` | arXiv 카테고리 (`cs.CV`) | OpenAlex **subfield명** (`Artificial Intelligence`) — `cat`으로 필터하는 로직이 있으면 대응 필요 |
| `citation_count` | Semantic Scholar | **OpenAlex** (snapshot 2026-02-03 고정) — 분포가 다르므로 실험 기록에 명시 |
| 수록 범위 | 자체 수집분 | view `bench-2512` = arXiv-backed CS ∧ cutoff 2025-12-31, **947,451편** |

⚠ **기존 FAISS 인덱스를 재사용하는 하이브리드는 금지** — corpus가 다르면 id 공간이 어긋난다.
반드시 새 디렉터리에 전체 빌드할 것.

**실제 사례 (2026-09-03)**: 이전 빌드 `database_cc-surveyeval-2512`(947,444편)에는 bench-2512 GT의
**preprint 쌍둥이 13편이 전부 살아 있다.** `surveyeval-2512` view의 제외 목록이 SurveyBench GT 20개라
bench GT를 거르지 않기 때문이다. 이 DB로 25 토픽을 돌리면 정답이 새어 실험이 무효가 되므로
`bench-2512`로 전체 재빌드했다. **view 이름과 DB 디렉터리 이름을 반드시 대조할 것.**

## 5. 재현성 기록

run 로그에 다음을 남기면 upstream까지 체인이 복원된다.
```
view = bench-2512
export content_sha256 = (bench-2512.surveyforge.json.manifest.json)
SURVEYFORGE_SURVEY_EXCLUDE_IDS = (설정 여부와 값 — 35개 합집합인지)
embedding model / paper_id_cutoff / paper_date_* 인자
--batch-size 와 PYTORCH_CUDA_ALLOC_CONF        # OOM 재발 시 원인 추적
빌드 소요 시간 / 처리량 (편/s)
```

`--batch-size`는 빌더가 `build_manifest.json`에 이미 남기므로 그 값을 인용하면 된다.

## 6. 참고

SurveyForge 쪽 상세 노트는 `../SurveyForge/docs/common-corpus-integration.md`.
코퍼스 쪽 일반론과 함정은 `docs/integration-guide.md` §2·§5-2.
