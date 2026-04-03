# VESSL 실행 가이드 (4 vCPU / 32GB)

## 1) 환경 준비
```bash
python -m pip install --upgrade pip
python -m pip install ortools z3-solver
```

## 2) 1차 스캔 (짧은 라운드)
```bash
python vessl_branch_runner.py \
  --a-start 0 --a-end 128 \
  --b-start 0 --b-end 64 \
  --per-branch-sec 20 \
  --workers 4 \
  --out round1.jsonl
```

## 3) 2차 스캔 (긴 라운드)
```bash
python vessl_branch_runner.py \
  --a-start 0 --a-end 128 \
  --b-start 0 --b-end 64 \
  --per-branch-sec 60 \
  --workers 4 \
  --out round2.jsonl
```

## 4) 상태 요약
```bash
python - <<'PY'
import json
from collections import Counter
for fn in ["round1.jsonl", "round2.jsonl"]:
    c=Counter()
    with open(fn,encoding='utf-8') as f:
        for line in f:
            r=json.loads(line)
            c[r['status']] += 1
    print(fn, dict(c))
PY
```

## 5) 후보가 나오면
- `CpSolverStatus.FEASIBLE` 또는 `CpSolverStatus.OPTIMAL`이 있는 `(low_a, low_b)`를 추출
- 해당 분기를 더 긴 시간(예: 600~1800초)으로 재실행
- `p,q`가 나오면 `verify_q7_solution.py`로 최종 검증

## 6) Z3 병렬 스캔 (보조 경로)
```bash
python vessl_z3_branch_runner.py \
  --a-start 0 --a-end 128 \
  --b-start 0 --b-end 64 \
  --per-branch-sec 20 \
  --workers 4 \
  --out z3_round1.jsonl
```

상태 요약:
```bash
python - <<'PY'
import json
from collections import Counter
for fn in ["z3_round1.jsonl"]:
    c=Counter()
    with open(fn,encoding='utf-8') as f:
        for line in f:
            r=json.loads(line)
            c[r['status']] += 1
    print(fn, dict(c))
PY
```
