from ortools.sat.python import cp_model
import argparse


def from_chunks(chunks):
    return int("".join(chunks), 16)


MASK = from_chunks(
    [
        "03ffffffffffffff",
        "fffff00fff000000",
        "0000000000000000",
        "0000000000000000",
        "0000000000000000",
        "0fffffffffffffff",
        "fffffffffff03fff",
        "ffffffffffffffff",
        "fffffffffc007ffc",
        "0000000000000000",
        "0000000000000000",
        "0000000000000000",
        "0000003fffffffff",
        "fffffffff03fffff",
        "ffffffffff80ffff",
        "ffffffffffffffff",
    ]
)

P_AND_MASK = from_chunks(
    [
        "025a5d0e209ba90e",
        "df4c800d9e000000",
        "0000000000000000",
        "0000000000000000",
        "0000000000000000",
        "0037ebe99c6fa249",
        "e4dd35d544300a41",
        "9e2e76eda236c193",
        "b0fc55ea440045ec",
        "0000000000000000",
        "0000000000000000",
        "0000000000000000",
        "0000000cb4c69974",
        "40d84318d03453e4",
        "6508185cfb80c0da",
        "b8321892e0c8cd83",
    ]
)

N = from_chunks(
    [
        "8feda8ccb480a97d",
        "8b8e216f84b5d637",
        "9110d6cf6604085a",
        "7a7acd9cf6a718db",
        "466ebbb71e286c67",
        "db91e69d87321304",
        "d3e0229cce11d61a",
        "27ba407ae375aee2",
        "6b4e4c0d9cebb737",
        "0d5ee46a2bb07130",
        "98aabfaf509140bf",
        "c4281236c07b38c9",
        "b66a5daf4bccbdef",
        "889fd5dbee02e22c",
        "beb46f4ce221a4f5",
        "c9bd7487dfe8faa2",
        "e12126ca1f7e8361",
        "74d75b6b02dfadb6",
        "ea65d9743b84c3fe",
        "d4c36238bb9dd6b6",
        "0110289ea421a817",
        "e6ab0b895b0a4266",
        "dfdaa48e8f55ccba",
        "9135ab8e30cf69f9",
        "15906470114fa178",
        "1725334dc51daae0",
        "723518ac6aca0430",
        "ba39533f8dd25f7e",
        "15004a631d390f38",
        "5c2af0adbabb0704",
        "bda087c1f75e64b4",
        "b52c4727051a2dc1",
    ]
)


def bit(x, i):
    return (x >> i) & 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--k-known", type=int, default=80)
    parser.add_argument("--max-time", type=float, default=3600.0)
    parser.add_argument("--presolve", action="store_true")
    parser.add_argument("--nq", type=int, default=1030)
    parser.add_argument("--low-a", type=int, default=-1, help="7-bit value for p bits 80..86")
    parser.add_argument("--low-b", type=int, default=-1, help="6-bit value for p bits 150..155")
    parser.add_argument("--q-top-one", action="store_true", help="force q[nq-1]=1")
    args = parser.parse_args()

    np = 1024
    nq = args.nq
    maxk = np + nq - 2  # 2052

    model = cp_model.CpModel()

    p = [None] * np
    q = [model.NewBoolVar(f"q{i}") for i in range(nq)]

    fixed_unknown = 0
    fixed_known = 0
    p_one_idx = []
    p_unknown_idx = []
    for i in range(np):
        m = bit(MASK, i)
        k = bit(P_AND_MASK, i)
        if m == 1:
            p[i] = k
            fixed_known += 1
            if k == 1:
                p_one_idx.append(i)
        else:
            v = model.NewBoolVar(f"p{i}")
            p[i] = v
            p_unknown_idx.append(i)
            fixed_unknown += 1

    print("p known bits", fixed_known, "p unknown bits", fixed_unknown)

    use_low_branch = (args.low_a >= 0 and args.low_b >= 0)
    if use_low_branch:
        if not (0 <= args.low_a < (1 << 7)):
            raise ValueError("--low-a must be in [0,127]")
        if not (0 <= args.low_b < (1 << 6)):
            raise ValueError("--low-b must be in [0,63]")

        # Fix low unknown holes explicitly.
        for b in range(7):
            idx = 80 + b
            vb = (args.low_a >> b) & 1
            if isinstance(p[idx], int):
                if p[idx] != vb:
                    raise ValueError("low-a conflicts with fixed bit")
            else:
                model.Add(p[idx] == vb)
        for b in range(6):
            idx = 150 + b
            vb = (args.low_b >> b) & 1
            if isinstance(p[idx], int):
                if p[idx] != vb:
                    raise ValueError("low-b conflicts with fixed bit")
            else:
                model.Add(p[idx] == vb)

    # Fix low q bits from known low p bits before first unknown p-bit.
    # First unknown p bit is at bit 80 (big-endian chunk interpretation).
    k_known = args.k_known
    if use_low_branch:
        if k_known > 230:
            raise ValueError("with --low-a/--low-b fixed, k_known must be <= 230")
    else:
        if k_known > 80:
            raise ValueError("k_known > 80 is invalid unless --low-a/--low-b are provided")
    p_low = P_AND_MASK & ((1 << k_known) - 1)
    if use_low_branch:
        for b in range(7):
            idx = 80 + b
            if idx < k_known:
                if (args.low_a >> b) & 1:
                    p_low |= 1 << idx
                else:
                    p_low &= ~(1 << idx)
        for b in range(6):
            idx = 150 + b
            if idx < k_known:
                if (args.low_b >> b) & 1:
                    p_low |= 1 << idx
                else:
                    p_low &= ~(1 << idx)
    n_low = N & ((1 << k_known) - 1)
    inv_p_low = pow(p_low, -1, 1 << k_known)
    q_low = (n_low * inv_p_low) % (1 << k_known)
    for i in range(k_known):
        model.Add(q[i] == ((q_low >> i) & 1))

    # Odd constraints
    model.Add(q[0] == 1)
    if isinstance(p[0], int):
        if p[0] != 1:
            raise RuntimeError("p0 must be 1 for odd N")
    else:
        model.Add(p[0] == 1)

    # carry bounds
    carry = [model.NewIntVar(0, 5000, f"c{k}") for k in range(maxk + 2)]
    model.Add(carry[0] == 0)

    # Build column equations
    for k in range(maxk + 1):
        terms = []
        i0 = max(0, k - (nq - 1))
        i1 = min(np - 1, k)
        for i in range(i0, i1 + 1):
            j = k - i
            if j < 0 or j >= nq:
                continue
            pi = p[i]
            qj = q[j]
            if isinstance(pi, int):
                if pi == 1:
                    terms.append(qj)
                else:
                    pass
            else:
                z = model.NewBoolVar(f"z_{i}_{j}")
                model.AddMultiplicationEquality(z, [pi, qj])
                terms.append(z)

        nbit = bit(N, k) if k < 2048 else 0
        lhs = sum(terms) + carry[k]
        model.Add(lhs == nbit + 2 * carry[k + 1])

    model.Add(carry[maxk + 1] == 0)

    # Require N exact bit length; top bit 2047 is 1 already from N.
    # q highest likely non-zero in this range for pruning
    if nq > 1024:
        model.Add(sum(q[1024:nq]) >= 1)
    if args.q_top_one:
        model.Add(q[nq - 1] == 1)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.max_time
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = True
    solver.parameters.cp_model_presolve = args.presolve
    solver.parameters.symmetry_level = 0

    print("Solving...")
    res = solver.Solve(model)
    print("status", res)
    if res in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        p_val = 0
        q_val = 0
        for i in range(np):
            b = p[i] if isinstance(p[i], int) else solver.Value(p[i])
            p_val |= int(b) << i
        for i in range(nq):
            q_val |= solver.Value(q[i]) << i
        print("p=", hex(p_val))
        print("q=", hex(q_val))
        print("check", p_val * q_val == N)


if __name__ == "__main__":
    main()
