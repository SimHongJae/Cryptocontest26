from math import gcd, isqrt
from z3 import BitVec, BitVecVal, Extract, Solver, ZeroExt, sat


def from_chunks(chunks):
    return int("".join(chunks), 16)


MASK = from_chunks([
    "03ffffffffffffff", "fffff00fff000000", "0000000000000000", "0000000000000000",
    "0000000000000000", "0fffffffffffffff", "fffffffffff03fff", "ffffffffffffffff",
    "fffffffffc007ffc", "0000000000000000", "0000000000000000", "0000000000000000",
    "0000003fffffffff", "fffffffff03fffff", "ffffffffff80ffff", "ffffffffffffffff",
])

PM = from_chunks([
    "025a5d0e209ba90e", "df4c800d9e000000", "0000000000000000", "0000000000000000",
    "0000000000000000", "0037ebe99c6fa249", "e4dd35d544300a41", "9e2e76eda236c193",
    "b0fc55ea440045ec", "0000000000000000", "0000000000000000", "0000000000000000",
    "0000000cb4c69974", "40d84318d03453e4", "6508185cfb80c0da", "b8321892e0c8cd83",
])

N = from_chunks([
    "8feda8ccb480a97d", "8b8e216f84b5d637", "9110d6cf6604085a", "7a7acd9cf6a718db",
    "466ebbb71e286c67", "db91e69d87321304", "d3e0229cce11d61a", "27ba407ae375aee2",
    "6b4e4c0d9cebb737", "0d5ee46a2bb07130", "98aabfaf509140bf", "c4281236c07b38c9",
    "b66a5daf4bccbdef", "889fd5dbee02e22c", "beb46f4ce221a4f5", "c9bd7487dfe8faa2",
    "e12126ca1f7e8361", "74d75b6b02dfadb6", "ea65d9743b84c3fe", "d4c36238bb9dd6b6",
    "0110289ea421a817", "e6ab0b895b0a4266", "dfdaa48e8f55ccba", "9135ab8e30cf69f9",
    "15906470114fa178", "1725334dc51daae0", "723518ac6aca0430", "ba39533f8dd25f7e",
    "15004a631d390f38", "5c2af0adbabb0704", "bda087c1f75e64b4", "b52c4727051a2dc1",
])

CT = from_chunks([
    "86e08d73037b174e", "d9548a5f1c9046bc", "93bdafd85f9150d7", "beef3fac7aa4a465",
    "fdbd7799b8f9cfd6", "9f50779441a821f1", "6dfd425ab95fdfdb", "cf62f458ee2f21a4",
    "d6fed55131d34922", "2a261c1f16e6967b", "595c5a4af92fb5fa", "1223b4bb6f306840",
    "74d17342fd05ce59", "6dbe9477bd647fcf", "0b870da0214d3d22", "4c5166453c0b84a6",
    "b555585246b265ee", "a28a1edfbdb5d7a6", "5f53f3f974cafdd4", "f4b7402f28127fed",
    "cffa6801a92de2b9", "12fd8b0ec8e85561", "d7acde03dc56201c", "88eaad6ede7ddbe0",
    "2c63cc0e6884a73f", "2de3f3a728735e19", "c0f03d0720f5d87c", "fdcd8d4696905c3f",
    "09e50d008697fb13", "54db0fa5a75eed1f", "a8f340953e1f5658", "ef75e94e471403ac",
])

E = 0x10001


def add_mask_constraints(s: Solver, p, width: int) -> None:
    for i in range(width):
        if (MASK >> i) & 1:
            s.add(Extract(i, i, p) == BitVecVal((PM >> i) & 1, 1))


def apply_low_branch(p_base: int, k_known: int, low_a: int, low_b: int) -> int:
    p_low = p_base & ((1 << k_known) - 1)
    for b in range(7):
        idx = 80 + b
        if idx < k_known:
            if (low_a >> b) & 1:
                p_low |= 1 << idx
            else:
                p_low &= ~(1 << idx)
    for b in range(6):
        idx = 150 + b
        if idx < k_known:
            if (low_b >> b) & 1:
                p_low |= 1 << idx
            else:
                p_low &= ~(1 << idx)
    return p_low


def run(np_bits: int = 1024, nq_bits: int = 1030, timeout_ms: int = 600000, k_known: int = 0, low_a: int = -1, low_b: int = -1):
    s = Solver()
    s.set(timeout=timeout_ms)

    p = BitVec("p", np_bits)
    q = BitVec("q", nq_bits)

    add_mask_constraints(s, p, np_bits)

    use_low = (low_a >= 0 and low_b >= 0)
    if use_low:
        # fix low unknown holes explicitly
        for b in range(7):
            idx = 80 + b
            s.add(Extract(idx, idx, p) == BitVecVal((low_a >> b) & 1, 1))
        for b in range(6):
            idx = 150 + b
            s.add(Extract(idx, idx, p) == BitVecVal((low_b >> b) & 1, 1))

    if k_known > 0:
        if not use_low and k_known > 80:
            raise ValueError("k_known > 80 requires low-a/low-b branch fixing")
        if use_low and k_known > 230:
            raise ValueError("with low-a/low-b fixed, k_known must be <= 230")
        p_low = PM & ((1 << k_known) - 1)
        if use_low:
            p_low = apply_low_branch(PM, k_known, low_a, low_b)
        mod = 1 << k_known
        q_low = ((N & (mod - 1)) * pow(p_low, -1, mod)) % mod
        for i in range(min(k_known, nq_bits)):
            s.add(Extract(i, i, q) == BitVecVal((q_low >> i) & 1, 1))

    # exact integer multiplication in widened bit-width (no modular wrapping)
    prod = ZeroExt(nq_bits, p) * ZeroExt(np_bits, q)
    total_w = np_bits + nq_bits
    s.add(prod == BitVecVal(N, total_w))

    # q odd; and enforce p <= sqrt(N) to remove factor order symmetry.
    s.add(Extract(0, 0, q) == BitVecVal(1, 1))
    s.add(ZeroExt(1, p) <= BitVecVal(isqrt(N), np_bits + 1))

    print(f"Solving with np={np_bits}, nq={nq_bits}, timeout={timeout_ms}ms, k_known={k_known}, low_a={low_a}, low_b={low_b}")
    r = s.check()
    print("status:", r)
    if r != sat:
        return None
    m = s.model()
    pv = int(str(m.evaluate(p, model_completion=True)))
    qv = int(str(m.evaluate(q, model_completion=True)))
    if pv * qv != N:
        print("model product mismatch")
        return None
    if (pv & MASK) != PM:
        print("mask mismatch")
        return None
    phi = (pv - 1) * (qv - 1)
    if gcd(E, phi) != 1:
        print("gcd mismatch")
        return None
    d = pow(E, -1, phi)
    mv = pow(CT, d, N)
    print(f"p={pv:x}")
    print(f"q={qv:x}")
    print(f"m={mv:x}")
    print("check (p & MASK) == PM:", (pv & MASK) == PM)
    print("check p*q == N:", pv * qv == N)
    print("check pow(m,e,N) == ct:", pow(mv, E, N) == CT)
    return pv, qv, mv


if __name__ == "__main__":
    import sys

    np_bits = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
    nq_bits = int(sys.argv[2]) if len(sys.argv) > 2 else 1030
    timeout_ms = int(sys.argv[3]) if len(sys.argv) > 3 else 600000
    k_known = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    low_a = int(sys.argv[5]) if len(sys.argv) > 5 else -1
    low_b = int(sys.argv[6]) if len(sys.argv) > 6 else -1
    run(np_bits=np_bits, nq_bits=nq_bits, timeout_ms=timeout_ms, k_known=k_known, low_a=low_a, low_b=low_b)
