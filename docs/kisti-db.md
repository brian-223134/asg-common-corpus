# KISTI 전달본 — Science Data Lake 파생 스토어 (`science_datalake_260825`)

**갱신: 2026-09-03** · 관련: [00-status-2026-08-27.md](00-status-2026-08-27.md) §1 (HF upstream) · [HANDOFF.md](HANDOFF.md)

KISTI 측이 구축해 전달한 **Science Data Lake 파생 스토어 패키지**를 이 머신에 받아 둔 기록이다.
이 문서는 **인벤토리·환경·접근 방법**만 정리한다. 프로젝트 파이프라인에 어떻게 붙일지는 §7에 제안으로만 적었고 결정하지 않았다.
모든 수치는 이 머신에서 실측한 값이며, 패키지 README에서 옮긴 값은 "README 기준"으로 표시했다.

---

## 0. 요약

| 항목 | 값 |
|---|---|
| 정체 | Science Data Lake(SDL)의 **파생 스토어** 핸드오버 패키지 — 논문 원문 KV + BM25 전문검색 색인 + 메타/그래프 DuckDB 7종 |
| 위치 | `/data2/chanjoong/kisti_data/science_datalake_260825/` (저장소 **밖**, 이동하지 않음 — §7.3) |
| 크기 | **410,857,190,146 bytes** = 410.9 GB(10진) = 383 GiB(`du -sh` → 383G) · 파일 **278개** |
| 논문 수 | **14,843,789편** 전편 원문 본문 포함 (README 기준) |
| 패키지 생성일 | 2026-08-25 (원본 서버 스냅샷) |
| 수신 완료 | 2026-09-03 (rsync) |
| 무결성 | `VERIFY.sh` (sha256, 277개) — §1.1 참조 |
| HF 배포판과의 관계 | **겹치는 파일 0개.** HF는 원본 parquet(메타데이터), 이 패키지는 그것을 가공한 조회·검색용 스토어 → 보완 관계 (§2) |

---

## 1. 입수 경위

- KISTI 측이 구축한 패키지를 2026-09-03 rsync로 수신했다. 원본 위치와 전송 실측(소요 시간·속도)은 이 문서에 기록하지 않는다.
- 패키지 README 자체 설명: "원본 parquet(`datasets/`, 2.4T)과 구색인 백업은 제외하고 실사용에 필요한 파생 스토어만 담음. 이 폴더 하나로 원문 조회·전문검색·메타/그래프 탐색이 전부 됨"

### 1.1 무결성 검증

패키지 동봉 `VERIFY.sh`(= `sha256sum -c SHA256SUMS`, 277개 파일 전부 재계산) 실행. 로그: `logs/verify_kisti_20260903_070542.log`.

| 파일 | 결과 | 해석 |
|---|---|---|
| `README.md` | **FAILED** | **전송 오류 아님.** 패키지 생성 측에서 `SHA256SUMS`·`MANIFEST.txt`를 만든 뒤(00:53) README를 다시 썼다(02:41; MANIFEST에는 13,207 bytes, 실제 9,425 bytes). 원본과 로컬의 README sha256이 `a3bb5754…`로 **동일**함을 확인 |
| 나머지 276개 | **검증 진행 중** — 07:09 현재 107개 OK, 실패 0 (README 제외). 완료 시 이 표 갱신 | |

### 1.2 겪은 함정 (다음 전송 때 재발 방지)

- **홈 디렉터리 777 → sshd가 키 무시.** 원본 측 계정 홈과 이 머신 `/data2/chanjoong` **둘 다** `drwxrwxrwx`였고, sshd 기본값(`StrictModes yes`)은 홈이 group/other-writable이면 `authorized_keys`를 읽지 않는다. `ssh-copy-id`가 "성공"해도 접속은 거부된다. 양쪽 모두 `chmod 755 ~`로 해결. (이 머신 홈은 755로 바꾼 채 둠.)
- **로그인 키에 암호구가 걸려 있음.** `~/.ssh/id_ed25519`(GitHub용)는 passphrase가 있어 `BatchMode`/무인 rsync에 못 쓴다. 전송 전용 무암호 키(`~/.ssh/id_kisti`)를 따로 만든 이유.
- **원본 셸에서 `ssh-copy-id`를 실행하면 자기 자신에게 등록된다.** 두 머신의 호스트명이 같아 실제로 헷갈렸다. 어느 셸인지는 `hostname -I`로 구분.

### 1.3 전송 후 정리 (미완료 항목 포함)

- [ ] 원본 측 계정의 `authorized_keys`에서 전송용 키 제거 요청: `sed -i '/kisti-transfer/d' ~/.ssh/authorized_keys`
- [ ] 같은 파일에 앞서 잘못 등록된 이 머신의 GitHub 키 2줄도 제거 요청
- [ ] 이 머신의 `~/.ssh/id_kisti{,.pub}` 삭제 (원본 측 등록 해제 후)

---

## 2. HF 배포판·기존 미러와의 관계

HF 저장소 `J0nasW/science-datalake`의 파일 목록(163개)을 직접 조회해 대조했다.

| | HF 배포판 (`J0nasW/science-datalake`) | **이 패키지** | 우리 미러 `data/upstream/cd87dd0/` |
|---|---|---|---|
| 내용 | 원본 parquet: `openalex/ sciscinet/ pwc/ xref/ ontologies/ p2p/ ros/ retwatch/` + `datalake.duckdb`(뷰 정의) | 파생 스토어: 원문 KV, BM25 색인, 메타·인용·저자 DuckDB | HF 중 OpenAlex 4테이블(works, works_topics, works_locations, topics 계층) 150 GB |
| 논문 원문 | **없음** | **14.8M편 전편** | 없음 |
| 파일 겹침 | — | HF와 **0개** | 이 패키지와 **0개** |
| 용도 | 메타데이터 대량 스캔 | 원문 조회·전문검색·그래프 탐색 | CorpusBuilder 입력 |

- 패키지에 동봉된 `CATALOG.md` / `SCHEMA.md` / `hf_dataset_card.md`는 **HF 원본 raw datasets를 설명하는 참고 문서**이고, 그 raw datasets는 이 패키지에 **없다** (README 명시). `datalake.json`의 `datasets.*.path`도 부재 경로를 가리킨다.
- `datalake.duckdb`(274 KB)는 뷰 정의만 담은 파일로, raw parquet가 없으므로 이 패키지에서는 열어도 뷰가 동작하지 않는다. 실제 데이터는 전부 `search/` 아래에 있다.
- "SDL 960 GB"(README §1, 00-status)는 **메타데이터 parquet 전체 설치** 기준(S2AG 437 + OpenAlex 262 + SciSciNet 151 GB 등)이며 원문이 아니다. SDL의 원문 파트는 별도로 통합본 130 GB(ZSTD parquet)·소스 합계 361 GB이고, 이 패키지의 `body_store.sqlite` 173 GB(zlib)가 그 통합 원문에 해당한다.
- 이 패키지의 원문 수(14,843,789)는 SDL 문서의 통합 원문 수(13.2M)보다 많다. arXiv를 40K → 878K로 늘리고 bioRxiv(43K)를 추가한 최신 빌드다.

---

## 3. 인벤토리 (실측 `du`)

```
science_datalake_260825/                 ← datalake 루트 (datalake.json이 앵커)
├── datalake.json / datalake.duckdb      루트 식별자 · 뷰 정의(이 패키지에선 비활성)
├── README.md                            패키지 사용 설명서 (한국어, 이 문서의 1차 출처)
├── CATALOG.md / SCHEMA.md / hf_dataset_card.md   HF 원본 raw datasets 참고 문서
├── MANIFEST.txt / SHA256SUMS / VERIFY.sh          전송 검증
├── requirements.txt / requirements_ml.txt
├── scripts/   (37개)  search_fulltext.py · config.py · build_*.py · convert_*.py · download_*.py …
├── eval/               검색 관련도 평가 하네스 (Track A known-item · Track B ad-hoc, qrels 포함)
└── search/             ★ 실제 데이터 전부
```

### 3.1 `search/` 스토어

| 파일 | 실측 | 내용 | 레코드 수 (README 기준) |
|---|---:|---|---|
| `body_store.sqlite` | **173G** | 논문 **원문 본문** KV — 테이블 `bodies(doi, tz)`, `tz`는 zlib 압축 텍스트 | 14,843,789 |
| `tantivy_body/` | **133G** (158 files) | **BM25 전문검색 색인** (tantivy, index_format **v7**, facet) | 14,843,789 docs |
| `paper_meta.duckdb` | 28G | 논문 마스터 `meta` (33컬럼) | 14,843,789 |
| `citation_graph.duckdb` | 16G | 인용 엣지 `edges(citing_doi, cited_doi)` | 115,258,420 |
| `paper_extras.duckdb` | 13G | 연도별 인용 · 온톨로지 · venue | ontology 148,069,224 / venue 13,682,066 |
| `paper_relations.duckdb` | 12G | 저자 · 키워드 · 토픽 | authors 84,425,638 / keywords 66,984,664 / topics 39,887,418 |
| `author_profiles.duckdb` | 7.9G | 저자 프로필 + 논문-저자 매핑 | profiles 16,305,612 / links 79,839,142 |
| `related_works.duckdb` | 1.5G | 관련논문 엣지 | 14,076,381 |
| `paper_pwc.duckdb` | 55M | Papers With Code (repo URL · framework · 공식 여부; **코드 자체는 없음**) | code 91,098 |

원문 관련(`body_store` + `tantivy_body`)만 306 GB로 전체의 3/4다.

### 3.2 원문 소스 구성 (README 기준)

| source | 건수 | 비중 |
|---|---:|---:|
| s2orc | 8,866,382 | 59.7% |
| pmc | 4,954,781 | 33.4% |
| arxiv | 877,920 | 5.9% |
| pes2o | 101,132 | 0.7% |
| biorxiv | 43,574 | 0.3% |

- DOI당 1부. 중복 제거 우선순위 `pmc > s2orc > pes2o > arxiv > biorxiv > core`.
- 초록 보유 13,891,226편(93.6%) · 철회 논문 34,760편 · 원문 평균 24.9 KB(압축 전).
- 원문은 **추출된 순수 텍스트**다(PDF·그림·LaTeX 소스 없음). 14.8M × 24.9 KB ≈ 370 GB가 zlib으로 173 GB.
- OpenAlex · S2AG · SciSciNet은 원문 소스가 아니라 **식별자 컬럼**(`openalex_id`, `s2ag_corpusid`, `sciscinet_paperid`)으로만 들어 있다.

---

## 4. 스키마 핵심 (README 기준; 전체 컬럼은 `PRAGMA table_info('<table>')`)

- **`paper_meta.meta`** (33컬럼): `doi, title, abstract, year, source, language, oa_type, cited_by_count, fwci, s2ag_citationcount, disruption, atypicality, team_size, patent_count, domain, field, subfield, primary_topic, is_retracted, retraction_reason, has_pwc, openalex_id, s2ag_corpusid, sciscinet_paperid, …`
- **`citation_graph.edges`**: `citing_doi, cited_doi`
- **`paper_relations`**: `authors(doi, author, orcid, is_corresponding, country)` · `keywords(doi, rank, keyword, score)` · `topics(doi, rank, topic, subfield, field, domain, score)`
- **`author_profiles`**: `profiles(author_id, name, orcid, h_index, works_count, cited_by_count, institution, country)` · `paper_author(doi, author_id, is_corresponding)`
- **`paper_extras`**: `citations_by_year(doi, year, cited_by_count)` · `ontology(doi, ontology, term, similarity)` · `venue(doi, journal, is_oa, license, oa_status)`
- **`paper_pwc`**: `code(doi, repo_url, framework, is_official)` · `methods` · `tasks` · `introduces` · `paper_map`
- **`body_store.bodies`**: `doi, tz` (zlib)
- 조인 키는 전부 **DOI**(소문자, `https://doi.org/` 접두사 없음). 우리 corpus의 OpenAlex work id와는 `meta.openalex_id`로 매핑한다.

---

## 5. 환경 요구사항 vs 현재 환경

| 패키지 | 원본(README) | 요구 | 현재 `asg-corpus` env | 판정 |
|---|---|---|---|---|
| python | 3.13 | tantivy `.so`를 **원본 venv에서 복사**할 때만 마이너 일치 필요 | **3.11.16** | pip 설치 경로면 무관할 것 — **미검증** |
| duckdb | 1.5.4 | ≥ 1.5.4 (그 버전으로 쓴 `.duckdb`) | **1.5.5** | OK |
| tantivy | 0.26.0 (index v7) | **정확히 0.26.0 계열** — 색인 포맷 호환 | **미설치** | `pip index versions tantivy` → 0.26.0 휠 존재. 설치·색인 오픈은 **미검증** |
| sqlite3 | — | 표준 라이브러리 | 3.53.4 | OK |

- `search_fulltext.py`의 실제 의존은 `duckdb`, `tantivy`, 표준 라이브러리(`sqlite3`, `zlib`)뿐이다. 동봉 `requirements.txt`의 pyarrow · pyoxigraph · rdflib 등은 **raw datasets 빌드/온톨로지용**이라 조회에는 불필요.
- 2026-09-03 시점에 **아무것도 설치하지 않았다**(문서화만). 설치는 `asg-corpus`에 `pip install "tantivy==0.26.0"` 한 줄로 시도 가능하지만, 실패 시 python 3.13 별도 env가 필요할 수 있다.

---

## 6. 접근 방법

### 6.1 루트 탐색

검색기(`scripts/config.py::find_datalake_root`)는 ① 스크립트 위치에서 위로 올라가며 `datalake.json`을 찾고, ② 없으면 `DATALAKE_ROOT` 환경변수를 본다. 스토어는 전부 `<루트>/search/`에서 찾는다.

```bash
export DATALAKE_ROOT=/data2/chanjoong/kisti_data/science_datalake_260825   # 외부에서 부를 때
```

### 6.2 동봉 CLI / 라이브러리 (README §4 요약; tantivy 설치 후)

```bash
cd /data2/chanjoong/kisti_data/science_datalake_260825
$PY scripts/search_fulltext.py "graph neural network" --top-k 10 --meta --snippets
$PY scripts/search_fulltext.py "diffusion model" --year-min 2020 --field "Computer Science" --min-citations 50 --exclude-retracted
$PY scripts/search_fulltext.py "CRISPR off-target" --source pmc --text        # 원문 전체
$PY scripts/search_fulltext.py "transformer attention" --json --meta          # JSON 출력
$PY scripts/search_fulltext.py --list --field "Physics" --year-min 2023 --order-by cited_by_count
```

```python
import sys; sys.path.insert(0, "scripts")
from search_fulltext import search, get_paper_bundle, list_papers
hits   = search("neural machine translation", top_k=20, year_min=2018, meta=True)
bundle = get_paper_bundle("10.xxxx/xxxxx")      # 원문+메타+저자+인용+관련논문
rows   = list_papers(field="Computer Science", year_min=2023, order_by="cited_by_count", top_k=100)
```

- facet 정규화 `norm()`은 `scripts/config.py`에 있고 색인 빌드와 검색이 공유한다. 이 파일이 있어야 `--field/--domain` 필터가 색인과 일치한다.
- 검색기는 `parse_query` 실패 시 특수문자를 제거하고 재시도하므로 임의 텍스트 질의에 크래시하지 않는다(README §6).

### 6.3 tantivy 없이 DuckDB · SQLite만으로 접근 (현재 env에서 바로 가능)

```python
import duckdb, sqlite3, zlib
ROOT = "/data2/chanjoong/kisti_data/science_datalake_260825/search"

con = duckdb.connect(f"{ROOT}/paper_meta.duckdb", read_only=True)
con.execute("PRAGMA table_info('meta')").fetchall()
con.execute("SELECT doi, title, year, source FROM meta WHERE openalex_id = ?", ["W2100837269"]).fetchall()

db = sqlite3.connect(f"file:{ROOT}/body_store.sqlite?mode=ro", uri=True)
(tz,) = db.execute("SELECT tz FROM bodies WHERE doi = ?", ["10.xxxx/xxxxx"]).fetchone()
text = zlib.decompress(tz).decode("utf-8")
```

여러 DuckDB 파일을 함께 쓰려면 `ATTACH '<path>' AS cg (READ_ONLY)` 후 `cg.edges`처럼 참조한다. **항상 read-only로 열 것** — 쓰기 모드로 열면 파일이 수정되어 `SHA256SUMS`와 어긋난다.

---

## 7. 프로젝트와의 연결 지점 (제안 — 결정 아님)

### 7.1 full-text 확보 범위 재검토 근거

[decisions.md](decisions.md) D8은 "원문 수집 채널이 arXiv e-print뿐"이라는 실측에서 full-text를 arXiv 한정으로 두었다.
이 패키지는 그 전제를 바꾼다: **비-arXiv 원문**(s2orc 8.9M, pmc 5.0M)이 로컬에 있고 DOI로 즉시 조회된다.
broader-CS(19.6M편) 채택을 막던 "full-text agent의 비-arXiv 논문 처리 불가"(D4)가 해소될 수 있다. 다만 커버리지는 실측 전이다: 우리 corpus의 OpenAlex id → `meta.openalex_id` 매핑률과 `has_full_text` 비율을 먼저 재야 한다.

### 7.2 FullTextResolver 프로바이더 후보

현재 `src/common_corpus/fulltext/`는 arXiv e-print → latex-v1 파서 경로만 있다. `body_store.sqlite` 조회를 제2 프로바이더로 두면 캐시 동결(version + sha256) 규약은 그대로 유지하면서 소스만 늘릴 수 있다. 텍스트 품질(s2orc/pmc 추출본 vs 우리 latex 파서)은 비교 필요.

### 7.3 위치 결정 — 보류

| 선택지 | 장점 | 단점 |
|---|---|---|
| **현재: `/data2/chanjoong/kisti_data/`** (저장소 밖) | SurveyX 등 다른 저장소에서도 같은 경로로 공유 | 프로젝트 관례(`data/upstream/<버전>/`)와 다름 |
| `data/upstream/science_datalake_260825/` | 업스트림이 한곳에 모임, `config/upstream.yaml` 상대경로 관례 유지, `data/`는 gitignore | 저장소 종속 |

두 경로는 같은 파일시스템(`/data2`)이라 `mv` 한 번으로 즉시 바뀐다. **2026-09-03: 이동하지 않고 현재 위치에 둔다.** 옮길 때 이 문서 §0의 위치와 `DATALAKE_ROOT`만 바꾸면 된다.

---

## 8. 남은 일

- [ ] `VERIFY.sh` 완료 결과 확정 (§1.1 갱신)
- [ ] 원본 측 `authorized_keys` 정리 요청 및 로컬 `id_kisti` 폐기 (§1.3)
- [ ] `asg-corpus`에 `tantivy==0.26.0` 설치 후 `search_fulltext.py` 스모크 (색인 v7 오픈 확인)
- [ ] 우리 corpus ↔ `paper_meta.meta.openalex_id` 매핑률 · `has_full_text` 커버리지 실측 (§7.1)
