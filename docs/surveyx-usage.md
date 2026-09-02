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

## 1. 설정 (`.env`)

`../SurveyX/.env`에서 데이터 소스를 공통 코퍼스로 돌리고 view를 지정한다.

```bash
SURVEYX_DATA_SOURCE=common_corpus
COMMON_CORPUS_DIR=/data2/chanjoong/survey-agent/asg-common-corpus
COMMON_CORPUS_VERSION=v0.1-poc
COMMON_CORPUS_VIEW=bench-2512          # ← 벤치마크 view. 기본값이 surveyeval-2512이므로 반드시 변경
COMMON_CORPUS_PYTHON=/data2/chanjoong/miniforge3/envs/asg-corpus/bin/python
COMMON_CORPUS_FULLTEXT_LIMIT=0         # 0 = 필터 통과분 전부
```

`COMMON_CORPUS_PYTHON`은 full text 확보를 asg-corpus conda env에 subprocess로 위임하는 데 쓴다
(SurveyX env에는 `common_corpus` 패키지가 없다).

`CommonCorpusFetcher`는 시작 시 parquet 두 개의 존재를 검사하고 실행 기록용 provenance로
`view` 이름과 `view_manifest_sha256`을 남긴다.

## 2. same-corpus 원칙에 따른 동작

- **온라인 검색 비활성**: `search_on_google()`은 항상 빈 리스트를 반환한다(`from` 필드만 유지).
  코퍼스 integration-guide §1의 불변 규칙 4.
- **검색 범위 = view**: cutoff와 GT 제외가 view에 이미 적용돼 있으므로 fetcher가 별도 필터를
  걸지 않는다. view 밖 id가 반환되면 버그다.
- **full text는 지연 확보**: `search_on_arxiv()` 단계에서는 채우지 않고, 임베딩 필터를 통과한
  논문에 대해서만 `fill_md_text()`로 FullTextResolver를 호출한다. 캐시는
  `data/fulltext_cache/arxiv/<id>/`에 version+sha256으로 동결된다.

## 3. 실행

```bash
cd /data2/chanjoong/survey-agent/SurveyX
python tasks/workflow/01_fetch_data.py --topic "<GT-SURVEYS.md의 Topic 열>" ...
python tasks/workflow/02_clean_data.py ...
python tasks/workflow/03_gen_outlines.py ...
python tasks/workflow/04_gen_content.py ...
python tasks/workflow/05_post_refine.py ...
python tasks/workflow/06_gen_latex.py ...
```

첫 실행은 arXiv e-print fetch 때문에 느리다(3초 politeness delay). 같은 논문이 다른 topic에서
재등장하면 캐시 히트로 네트워크 0이다. **25개 topic을 순차로 돌리면 뒤로 갈수록 빨라진다.**

## 4. 함정

- **`md_text` 부재 시 KeyError**: 원 코드 두 곳에서 `md_text`를 무조건 참조한다
  (`SurveyX/REPRODUCTION.md` §3.1). full text 확보에 실패한 논문(파싱 실패·PDF only)에 대한
  가드가 필요하다. FullTextResolver는 실패도 기록하므로 명시적으로 지우기 전까지 재시도하지 않는다.
- **authors 없음**: v1 corpus에는 저자가 없다. BibTeX 생성은 `make_bibtex()`가 arXiv 메타에서
  보강한다 — 생성된 BibTeX의 author 필드를 스모크로 확인할 것.
- **view 이름 기본값**: `COMMON_CORPUS_VIEW` 기본값이 `surveyeval-2512`다. 벤치마크 실행 전
  `bench-2512`로 바꿨는지 반드시 확인한다(로그의 provenance 라인에 찍힌다).
- **키워드 검색의 리콜**: ILIKE 스캔은 임베딩 검색보다 리콜이 낮다. 이는 원 SurveyX 설계
  (키워드 recall → 임베딩 필터)를 그대로 옮긴 것이며, agent 간 차이가 아니라 agent 고유 특성이다.

## 5. 재현성 기록

```
view = bench-2512
view_manifest_sha256 = (fetcher가 로그에 남김)
fulltext cache = data/fulltext_cache/arxiv/<id>/metadata.json 의 version+sha256
```

## 6. 참고

SurveyX 쪽 재현 계획은 `../SurveyX/REPRODUCTION.md`, 코퍼스 쪽 일반론은
`docs/integration-guide.md` §5-3. full text 확보 범위의 한계(비-arXiv 25%만 PDF 확보 가능)는
`docs/decisions.md` D8.
