# SurveyX에서 Common Corpus 사용하기 (DataFetcher 1클래스 대체)

**대상 view**: `bench-2512` (947,451편) · GT 목록은 `candidates/GT-SURVEYS.md`

SurveyX는 원래 사내 인프라(오프라인 arXiv Elasticsearch + Google Scholar 크롤러 + MongoDB)에
의존해 **그대로는 재현 불가**다. 이를 공통 코퍼스로 대체하는 구현이 SurveyX 쪽에 이미 있다:
`src/modules/preprocessor/common_corpus_fetcher.py` (`CommonCorpusFetcher`).

다른 세 agent와 달리 **export JSON을 쓰지 않는다.** parquet + view를 직접 조회한다.

## 0. 이 agent만 다른 점

| | AutoSurvey / SurveyForge / LLM×MR-V2 | **SurveyX** |
|---|---|---|
| 입력 | `data/exports/<view>.<format>.json` | `data/corpus/v0.1-poc/papers.parquet` ⋈ `data/views/<view>/paper_ids.parquet` |
| 검색 | 임베딩 + FAISS | **키워드 ILIKE 스캔**(원 코드의 제목/초록 부분 문자열 매칭과 동일 시맨틱) → 이후 자체 임베딩 필터 |
| full text | 불필요 / pool 전체 | **AttributeTree가 `md_text`를 요구** → FullTextResolver로 지연 확보 |
| 인덱스 | 임베딩 빌드 필요 (AutoSurvey 1h18m · SurveyForge GPU 빌드) | **불필요** — 사전 구축 인덱스가 없다. 키워드당 0.9~1.2초 ILIKE 스캔(bench-2512 cold 실측)이고, 임베딩 인덱스는 리콜분(~1,300편)에 대해 **실행마다 in-memory 생성**(`paper_filter.py:50`) |
| 입력 인자 | Topic 문자열 1개 | **Topic 문자열을 `--title`·`--key_words` 양쪽에** (§3) |

## 1. 설정 (`.env`)

`../SurveyX/.env`에서 데이터 소스를 공통 코퍼스로 돌리고 view를 지정한다.

```bash
SURVEYX_DATA_SOURCE=common_corpus
COMMON_CORPUS_DIR=/data2/chanjoong/survey-agent/asg-common-corpus
COMMON_CORPUS_VERSION=v0.1-poc
COMMON_CORPUS_VIEW=bench-2512          # ← 벤치마크 view (코드 기본값도 동일)
COMMON_CORPUS_PYTHON=/data2/chanjoong/miniforge3/envs/asg-corpus/bin/python
COMMON_CORPUS_FULLTEXT_LIMIT=0         # 0 = 필터 통과분 전부

# BibTeX 보강용 (없어도 파이프라인은 돌지만 author/venue 필드가 빔)
ARXIV_SNAPSHOT_DUCKDB=/data2/chanjoong/survey-agent/survey-search/data/papers.duckdb
COMMON_CORPUS_VENUE_LOOKUP=            # 기본값 ../SurveyX/datasets/venue_lookup.parquet
```

`COMMON_CORPUS_PYTHON`은 full text 확보를 asg-corpus conda env에 subprocess로 위임하는 데 쓴다
(SurveyX env에는 `common_corpus` 패키지가 없다).

`COMMON_CORPUS_VENUE_LOOKUP`은 **선행 1회 빌드가 필요하다** — SurveyX 쪽에서
`python scripts/build_venue_lookup.py` (OpenAlex 미러 `works_locations` 스캔, 1~2분).
실측 256,760편 수록, bench-2512 기준 커버리지 **27.1%**(256,573편). 이 두 소스가 없으면
§4의 "make_bibtex()가 arXiv 메타에서 보강한다"가 성립하지 않는다.

`CommonCorpusFetcher`는 시작 시 parquet 두 개의 존재를 검사하고 실행 기록용 provenance로
`view` 이름과 `view_manifest_sha256`을 남긴다.

## 2. same-corpus 원칙에 따른 동작

- **온라인 검색 비활성**: `search_on_google()`은 항상 빈 리스트를 반환한다(`from` 필드만 유지).
  코퍼스 integration-guide §1의 불변 규칙 4.
- **검색 범위 = view**: cutoff와 GT 제외가 view에 이미 적용돼 있으므로 fetcher가 별도 필터를
  걸지 않는다. view 밖 id가 반환되면 버그다.
- **full text는 지연 확보**: `search_on_arxiv()` 단계에서는 채우지 않고, 임베딩 필터를 통과한
  논문에 대해서만 `fill_md_text()`로 FullTextResolver를 호출한다(`preprocessor.py:62-66`).
  캐시는 asg-common-corpus 쪽 `data/fulltext_cache/arxiv/<id>/`에 version+sha256으로 동결된다.

## 3. 실행

```bash
cd /data2/chanjoong/survey-agent/SurveyX
python tasks/full_run.py \
    --title "<GT-SURVEYS.md의 Topic 열>" \
    --key_words "<같은 Topic 문자열>"
```

`full_run.py` 하나가 preprocessing(리콜→필터→전문확보→AttributeTree) + 아웃라인 +
본문 + 사후정제 + LaTeX 컴파일까지 전부 수행한다.

⚠ **`--key_words`에 Topic 문자열을 그대로 한 번 더 넣는다 — SurveyX만의 예외다.**
다른 3 agent는 Topic 문자열이 검색에 직접 들어가지만, SurveyX는 키워드에서 LLM으로
topic 서술을 재생성해 그것으로 필터·아웃라인·본문을 만든다. `--key_words`를 비우면:

- `generate_keyword.md`가 "이미 키워드가 있다"는 전제로 **추가** 3~4개만 요구 → 핵심어 누락
- `generate_topic.md`는 `{key_word}`만 받고 **title을 보지 않는다** (`utils.py:104`가 title을
  `load_prompt`에 넘기지만 템플릿이 쓰지 않는다)

2026-09-03 실측(title-only, 즉시 중단): "Instruction Tuning for Large Language Models"에
대해 키워드가 `natural language processing, language model fine-tuning, artificial
intelligence, transformer architecture`로 나오고 topic 문장에 "instruction tuning"이
한 번도 등장하지 않았다. Topic 문자열을 시드로 주면 `utils.py:116`의 `>=6` 게이트와
`utils.py:128-131` 분기가 시드를 보존한 채 LLM 확장 3개를 덧붙인다. 사람 입력은
여전히 Topic 문자열 하나뿐이라 25편에 기계적으로 동일 적용된다.

⚠ **`tasks/workflow/01~06`을 순차로 쓰지 말 것.** `--topic` 인자는 존재하지 않고
(`parse_arguments_for_preprocessor`는 `--title/--key_words/--page/--time_s/--time_e/
--enable_cache`만 받는다), `01_fetch_data.py`가 부르는 `single_preprocessing()`이
DataCleaner까지 이미 수행하므로(`preprocessor.py:74`) `02_clean_data.py`를 이어 돌리면
정제가 2번 돌아 비용의 61%를 차지하는 AttributeTree가 중복된다.

### 비용·시간 실측 (llama-3.3-70b, `CHAT_AGENT_WORKERS=4`)

| | 값 |
|---|---|
| 1편 | 3시간 07분 / **$2.28** (2026-08-31 Edge Computing, 문헌 199편) |
| 25편 환산 | ≈ **78시간 / $57** |
| 비용 집중 | AttributeTree 61% + 본문생성 26% = **87%** |

첫 실행은 arXiv e-print fetch 때문에 느리다(3초 politeness delay). 다만 **캐시 효과는
기대하지 말 것** — `SELECTION.md` 실측으로 25편 쌍별 GT ref 중복이 최대 6.1%,
도메인 간 평균 1% 미만이고 현재 fulltext 캐시도 437편(24MB, 2026-09-03)뿐이다. 25편 대부분이
신규 fetch이므로 전문 확보 20~25분/편을 그대로 계상한다.

## 4. 함정

- **`md_text` 부재 가드 — 이미 구현됨**: 원 코드 두 곳의 무조건 `md_text` 참조
  (`SurveyX/REPRODUCTION.md` §3.1)는 C0 가드 2건으로 처리 완료다
  (`DataCleaner.quick_check()`의 md_text 필수조건 제거, `complete_abstract()` skip 가드).
  **추가 조치 불필요.** FullTextResolver는 **영구 오류만** `failure.json`으로 동결한다
  (파싱 실패, 본문 500자 미만 등) — 이 경우에만 `SurveyX/scripts/fetch_fulltext_batch.py
  --retry-failed`가 필요하다. 429·타임아웃 같은 일시적 오류는 동결하지 않으므로
  (`resolver.py:72-77`의 `is_transient` 분기) **재실행이 곧 재시도**다. 잠깐의 429로
  논문이 영구히 pool 밖으로 빠져 pool 구성이 실행 시점에 좌우되는 것을 막는 장치다.
- **authors 없음**: v1 corpus에는 저자가 없다. BibTeX 생성은 `make_bibtex()`가
  `ARXIV_SNAPSHOT_DUCKDB`(저자)와 venue lookup(출판처)에서 보강한다. Edge 산출물 실측으로
  저자 88%(175/199)·venue 32%(64/199) 표기 — 생성된 BibTeX의 author 필드를 스모크로 확인할 것.
- **view 이름**: 코드 기본값은 `bench-2512`다(SurveyX 커밋 `16d4333` 이후). 구 view
  `surveyeval-2512`가 `.env`에 남아 있지 않은지 실행 로그의 provenance 라인으로 확인한다.
  두 view의 제외 id 집합은 **완전히 disjoint**(구 GT 20편 ↔ 신 GT 15 id)이므로,
  구 view로 벤치마크를 돌리면 GT 쌍둥이 13편이 검색 범위에 그대로 노출된다 — 취향이
  아니라 **누수**다.
- **키워드 검색의 리콜**: ILIKE 스캔은 임베딩 검색보다 리콜이 낮다. 이는 원 SurveyX 설계
  (키워드 recall → 임베딩 필터)를 그대로 옮긴 것이며, agent 간 차이가 아니라 agent 고유 특성이다.

## 5. 재현성 기록

```
view = bench-2512
view_manifest_sha256 = d4c16c499ecbff88c08387c48784f7cd2f759b4ee6928f2af67655c2866c0d86
fulltext cache = data/fulltext_cache/arxiv/<id>/metadata.json 의 version+sha256
```

## 6. 참고

SurveyX 쪽 재현 계획은 `../SurveyX/REPRODUCTION.md`, 어댑터 설계 정본은
`../SurveyX/docs/common-corpus-adapter.md`, 실행 실측 기록은 `../SurveyX/docs/experiments/`.
코퍼스 쪽 일반론은 `docs/integration-guide.md` §5-3. full text 확보 범위의 한계
(비-arXiv 25%만 PDF 확보 가능)는 `docs/decisions.md` D8.
