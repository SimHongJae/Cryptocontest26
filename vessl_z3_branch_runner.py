import argparse
import json
import os
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
Z3_SOLVER = os.path.join(BASE_DIR, "solve_q7_z3_exact.py")


def run_one(job):
    a, b, sec = job
    cmd = [
        "python",
        Z3_SOLVER,
        "1024",
        "1024",
        str(int(sec * 1000)),
        "230",
        str(a),
        str(b),
    ]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    st = "NO_STATUS"
    for line in p.stdout.splitlines():
        if line.startswith("status:"):
            st = line.split(":", 1)[1].strip()
    if p.returncode != 0 and st == "NO_STATUS":
        st = "ERROR"
    return {
        "a": a,
        "b": b,
        "status": st,
        "seconds": round(dt, 3),
        "returncode": p.returncode,
        "stderr_head": (p.stderr or "").splitlines()[:2],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a-start", type=int, default=0)
    ap.add_argument("--a-end", type=int, default=128)
    ap.add_argument("--b-start", type=int, default=0)
    ap.add_argument("--b-end", type=int, default=64)
    ap.add_argument("--per-branch-sec", type=int, default=20)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="vessl_z3_results.jsonl")
    args = ap.parse_args()

    jobs = [(a, b, args.per_branch_sec) for a in range(args.a_start, args.a_end) for b in range(args.b_start, args.b_end)]
    total = len(jobs)
    done = 0
    with open(args.out, "w", encoding="utf-8") as f:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(run_one, j) for j in jobs]
            for fut in as_completed(futs):
                r = fut.result()
                done += 1
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                if done % 20 == 0:
                    print(f"[z3-runner] {done}/{total} last=({r['a']},{r['b']}) {r['status']}", flush=True)

    print(f"[z3-runner] done total={total} out={args.out}")


if __name__ == "__main__":
    main()
