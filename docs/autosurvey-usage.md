# AutoSurvey에서 Common Corpus 사용하기 (경로 B — 코드 수정 0줄)

**대상 view**: `bench-2512` (benchmark 확정본, 947,451편) · GT 목록은 `candidates/GT-SURVEYS.md`

**결정 배경**: survey-search 경유(경로 A)는 쓰지 않기로 함(2026-08-31, docs/decisions.md D3).
AutoSurvey의 기존 DB 포맷을 Common Corpus에서 그대로 생성해 `--db_path`만 바꾼다.

## 0. 준비된 입력 (이 프로젝트가 이미 만들어 둔 것)

| 파일 | 내용 |
|---|---|
| `data/exports/bench-2512.autosurvey.json` | **947,451편**, TinyDB `{"cs_paper_info": {...}}`, 필드 `id,title,url,date,abs,cat` (1.21GB) |
| 같은 경로 `.manifest.json` | view→corpus→upstream sha 체인 (실험 기록에 인용) |

- view `bench-2512` = cutoff **2025-12-31** + GT preprint 쌍둥이 13건 제외 (D9 확정본).
  다른 cutoff/GT로 새 view가 필요할 때만:
  ```bash
  cd /data2/chanjoong/survey-agent/asg-common-corpus
  /data2/chanjoong/miniforge3/envs/asg-corpus/bin/python -m common_corpus.cli create-view \
      --name <실험명> --cutoff <YYYY-MM-DD> --exclude-file candidates/gt_exclude.txt
  /data2/chanjoong/miniforge3/envs/asg-corpus/bin/python -m common_corpus.cli export-agent-db \
      --view <실험명> --format autosurvey
  ```

## 1. AutoSurvey 쪽 DB 디렉터리 구성 + 임베딩 빌드 (1회, GPU)

```bash
cd /data2/chanjoong/survey-agent/AutoSurvey
mkdir -p database_commoncorpus-bench-2512
cp ../asg-common-corpus/data/exports/bench-2512.autosurvey.json \
   database_commoncorpus-bench-2512/arxiv_paper_db.json
cp ../asg-common-corpus/data/exports/bench-2512.autosurvey.json.manifest.json \
   database_commoncorpus-bench-2512/

# conda autosurvey env + 유휴 GPU 확인(nvidia-smi) 후 — 908K 기준 약 30분
conda run -n autosurvey python scripts/build_index.py \
    --db-path ./database_commoncorpus-bench-2512 --device cuda
```

`build_index.py`가 `database.py`가 읽는 이름 그대로 생성한다:
`faiss_paper_title_embeddings.bin`, `faiss_paper_abs_embeddings.bin`, `arxivid_to_index_abs.json`.

검증: `conda run -n autosurvey python scripts/check_db.py --db-path ./database_commoncorpus-bench-2512 --verify-embeddings 20`

## 2. 실행 — 바꾸는 것은 --db_path 하나

```bash
python main.py --topic "..." --db_path ./database_commoncorpus-bench-2512 \
    --embedding_model nomic-ai/nomic-embed-text-v1 ...   # 나머지 인자 기존과 동일
```

- `--embedding_model`은 인덱스를 만든 모델과 **반드시 동일**해야 함 (build_index.py 주석)
- GT 제외는 view 단계에서 이미 적용됨 — retrieval 단계 제외 로직 불필요

## 3. 알아둘 차이점 (기존 database_2026-08 대비)

| 항목 | 기존 | Common Corpus DB |
|---|---|---|
| `id` | `1811.06122v1` (버전 접미사) | **`1811.06122` (base id)** — 코드에는 불투명 키라 무해. 교차 비교 시 base id로 정합 |
| `date` | arXiv 수집 날짜 | `first_public_date` (53% day / 47% month 정밀도, month는 월초) |
| `cat` | arXiv 카테고리 (`cs.IT`) | OpenAlex **subfield명** (`Artificial Intelligence`) — 런타임 미사용 필드라 무해 |
| `authors` | 있음 | **없음** — 런타임 미사용. 후처리(enrich_references.py)는 arXiv API로 어차피 별도 조회 |
| 수록 범위 | ~2026-08-04, 909K | **~2026-02-03(OpenAlex snapshot) ∧ cutoff 2025-12-31**, view `bench-2512` 947,451편 |
| citation | 없음 | (autosurvey 포맷엔 미포함, surveyforge 포맷에 있음) |

⚠ 결과 비교 시 이 DB로 만든 실험은 기존 스냅샷 실험과 **corpus가 다르므로** 같은 축에 놓지 말 것.
run 기록에 `database_commoncorpus-bench-2512/*.manifest.json`의 sha를 남기면 재현 체인이 완성된다.

## 4. 문제 발생 시

- 임베딩 OOM → `--batch-size 128`
- `cs_paper_info` KeyError → export 파일이 옛 버전(`_default`) — asg-common-corpus에서 재export (커밋 `8339ee7` 이후)
- 검색 결과에 GT survey가 보임 → view의 `--exclude-file` 목록 확인 후 재export

## 5. 다른 agent 문서

`docs/surveyforge-usage.md` · `docs/surveyx-usage.md` · `docs/llmxmapreduce-v2-usage.md`.
LLM×MapReduce-V2는 여기서 만든 `database_commoncorpus-bench-2512`를 retrieval 백엔드로 재사용한다.
