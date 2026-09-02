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
CUDA_VISIBLE_DEVICES=<idle> .venv/bin/python scripts/build_db_from_corpus.py \
    --export ../asg-common-corpus/data/exports/bench-2512.surveyforge.json \
    --out $SURVEYFORGE_DATA/database_cc-bench-2512
# 스모크: --limit 2000 --skip-survey-assets --out <scratch>
# 검증  : scripts/check_db.py --db <out> --verify-embeddings 20
```

빌더가 지키는 불변식(해당 스크립트 헤더에 실측으로 문서화됨):
```
TinyDB 키 == arxivid_to_index_abs.json 값 == IndexIDMap stored id (1-based 연속)
faiss_paper_title_abs_* = encode(title + abs)   # 구분자 없는 단순 연결
faiss_paper_title_*     = encode(title)
IndexIDMap(IndexFlatIP), 1024-dim, L2 정규화, instruction prefix 없음
```
임베딩은 청크(기본 25,600편) 단위 체크포인트라 중단 후 같은 명령으로 재시작 가능하다.

## 2. ⚠ Outline DB는 별도로 GT를 제외해야 한다

SurveyForge는 논문 DB 외에 **Survey Outline DB**(별도 20K편)를 쓴다. 이 DB는 **공통 corpus 범위 밖**이라
view의 GT 제외가 적용되지 않는다 — 벤치마크 GT survey가 아웃라인 예시로 검색될 수 있다.

`code/src/database.py`가 환경변수로 거르는 경로를 제공한다:

```bash
export SURVEYFORGE_SURVEY_EXCLUDE_IDS="$(paste -sd, ../asg-common-corpus/candidates/gt_exclude.txt)"
```

`gt_exclude.txt`의 15개 id(GT 본체 2 + preprint 쌍둥이 13)를 쉼표로 이어 넣는다.
**이 단계를 빠뜨리면 outline 단계에서 정답이 새어 실험이 무효가 된다.**

## 3. 실행

```bash
cd /data2/chanjoong/survey-agent/SurveyForge/code
python main.py --topic "<GT-SURVEYS.md의 Topic 열>" \
    --db_path $SURVEYFORGE_DATA/database_cc-bench-2512 \
    --embedding_model ./gte-large-en-v1.5 \
    --paper_date_newest 2025-12-31 \
    ...   # 나머지 인자는 기존 실험과 동일하게 고정
```

- `--embedding_model`은 인덱스를 만든 모델과 **반드시 동일**해야 한다.
- `--paper_id_cutoff` / `--paper_date_oldest` / `--paper_date_newest`는 **방어적 이중 게이트**다.
  cutoff는 view에서 이미 적용됐으므로 view와 어긋나지 않게 맞춘다(`SURVEYFORGE_PAPER_DATE_NEWEST`
  기본값 `2024-09-26`을 그대로 두면 corpus보다 더 좁게 잘린다 — 반드시 확인할 것).
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

## 5. 재현성 기록

run 로그에 다음을 남기면 upstream까지 체인이 복원된다.
```
view = bench-2512
export content_sha256 = (bench-2512.surveyforge.json.manifest.json)
SURVEYFORGE_SURVEY_EXCLUDE_IDS = (설정 여부와 값)
embedding model / paper_date_* 인자
```

## 6. 참고

SurveyForge 쪽 상세 노트는 `../SurveyForge/docs/common-corpus-integration.md`.
코퍼스 쪽 일반론과 함정은 `docs/integration-guide.md` §2·§5-2.
