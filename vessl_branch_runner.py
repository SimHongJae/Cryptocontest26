import argparse
import json
import os
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed


def run_one(job):
    low_a, low_b, sec, nq, q_top_one = job
    cmd = [
        "python",
        "cp_sat_factor.py",
        "--max-time",
        str(sec),
        "--k-known",
        "230",
        "--nq",
        str(nq),
        "--low-a",
        str(low_a),
        "--low-b",
        str(low_b),
    ]
    if q_top_one:
        cmd.append("--q-top-one")

    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0

    status = "UNKNOWN"
    p_hex = None
    q_hex = None

    for line in p.stdout.splitlines():
        if line.startswith("status "):
            status = line.split()[-1]
        elif line.startswith("p="):
            p_hex = line.split("=", 1)[1].strip()
        elif line.startswith("q="):
            q_hex = line.split("=", 1)[1].strip()

    return {
        "low_a": low_a,
        "low_b": low_b,
        "status": status,
        "seconds": round(dt, 3),
        "returncode": p.returncode,
        "p": p_hex,
        "q": q_hex,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a-start", type=int, default=0)
    ap.add_argument("--a-end", type=int, default=128)
    ap.add_argument("--b-start", type=int, default=0)
    ap.add_argument("--b-end", type=int, default=64)
    ap.add_argument("--per-branch-sec", type=int, default=20)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--nq", type=int, default=1024)
    ap.add_argument("--q-top-one", action="store_true")
    ap.add_argument("--out", default="vessl_branch_results.jsonl")
    args = ap.parse_args()

    jobs = []
    for a in range(args.a_start, args.a_end):
        for b in range(args.b_start, args.b_end):
            jobs.append((a, b, args.per_branch_sec, args.nq, args.q_top_one))

    total = len(jobs)
    print(f"[runner] jobs={total} workers={args.workers} per_branch={args.per_branch_sec}s")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    done = 0
    sat_like = 0
    with open(args.out, "w", encoding="utf-8") as f:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(run_one, j) for j in jobs]
            for fut in as_completed(futs):
                r = fut.result()
                done += 1
                if r["status"] in ("CpSolverStatus.FEASIBLE", "CpSolverStatus.OPTIMAL"):
                    sat_like += 1
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                if done % 20 == 0 or r["status"] in ("CpSolverStatus.FEASIBLE", "CpSolverStatus.OPTIMAL"):
                    print(f"[runner] {done}/{total} sat_like={sat_like} last=({r['low_a']},{r['low_b']}) {r['status']}")

    print(f"[runner] done total={total} sat_like={sat_like} out={args.out}")


if __name__ == "__main__":
    main()
