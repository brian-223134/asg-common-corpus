#!/usr/bin/env bash
# refs.json이 없는 모든 후보에 대해 순차 추출 (S2 rate limit 고려, 실패해도 계속)
set -u
cd "$(dirname "$0")/.."
PY=/data2/chanjoong/miniforge3/envs/asg-corpus/bin/python
for y in candidates/*/*/candidate.yaml; do
    d=$(dirname "$y")
    [ -f "$d/refs.json" ] && continue
    echo "=== $d"
    "$PY" scripts/extract_gt_refs.py --candidate "$d" || echo "FAILED: $d"
    sleep 2
done
"$PY" scripts/audit_candidates.py --cutoff 2025-12-31
