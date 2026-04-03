from pathlib import Path
import sys
import z3

from solve8 import SBOX, sb, sr, mc, constrain_round_keys, parse_leaked, add_known_bits
from scan_base_survival import mix_col, inv_mix_col, fill, K11_CANDS


def derive_tuple(p: bytes, leak, k10: int, x2mask: int, k15: int):
    y = [SBOX[b] for b in p]
    x1_0 = 0x20
    k0_0 = mix_col([y[0], y[5], y[10], y[15]])[0] ^ x1_0
    x2 = leak[2]
    x2vals = [fill(x2[i], (x2mask >> i) & 1) for i in range(4)]
    for k5 in range(256):
        x1_bundle = [
            mix_col([y[0], y[5], y[10], y[15]])[0] ^ k0_0,
            mix_col([y[4], y[9], y[14], y[3]])[0] ^ k5,
            mix_col([y[8], y[13], y[2], y[7]])[0] ^ k10,
            mix_col([y[12], y[1], y[6], y[11]])[0] ^ k15,
        ]
        y1 = [SBOX[x1_bundle[0]], SBOX[x1_bundle[1]], SBOX[x1_bundle[2]], SBOX[x1_bundle[3]]]
        w1 = mix_col(y1)
        k1col0 = [x2vals[i] ^ w1[i] for i in range(4)]
        pre = inv_mix_col(k1col0)
        if pre[0] == k5:
            return k0_0, pre[0], pre[1], pre[2], pre[3]
    return None


def check_tuple(p: bytes, c: bytes, leak, k10: int, x2mask: int, k15: int, timeout_ms: int):
    tup = derive_tuple(p, leak, k10, x2mask, k15)
    if tup is None:
        return z3.unsat
    k0_0, k5, k8, k6, k3 = tup
    s = z3.SolverFor("QF_BV")
    s.set("threads", 8)
    s.set("timeout", timeout_ms)
    k = [z3.BitVec(f"K_{j}", 8) for j in range(16)]
    fixed = {0: k0_0, 3: k3, 5: k5, 6: k6, 8: k8, 10: k10, 15: k15}
    for j, v in fixed.items():
        s.add(k[j] == z3.BitVecVal(v, 8))
    s.add(z3.Or([k[11] == z3.BitVecVal(v, 8) for v in K11_CANDS]))
    rk = constrain_round_keys(s, k)
    xs = [[z3.BitVecVal(x, 8) for x in p]]
    for r in range(7):
        y = sb(xs[r]); z = sr(y); w = mc(z)
        xs.append([w[t] ^ rk[r][t] for t in range(16)])
    for j, b in enumerate(c):
        s.add(xs[7][j] == z3.BitVecVal(b, 8))
    add_known_bits(s, xs, leak)
    return s.check()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: scan_k10_family.py <hex_k10>")
    k10 = int(sys.argv[1], 16)
    base = Path(__file__).resolve().parent
    pt = (base / "plaintext.bin").read_bytes()
    ct = (base / "ciphertext.bin").read_bytes()
    leak = parse_leaked(base / "leaked.txt")
    i = 28178
    p = pt[i * 16:(i + 1) * 16]
    c = ct[i * 16:(i + 1) * 16]

    unknowns: list[tuple[int, int]] = []
    for x2mask in range(16):
        kept = False
        for k15 in range(256):
            res = check_tuple(p, c, leak, k10, x2mask, k15, 50)
            if res == z3.sat:
                print(f"k10={k10:02x} x2mask={x2mask:x} immediate SAT at k15={k15:02x}")
                kept = True
                break
            if res == z3.unknown:
                unknowns.append((x2mask, k15))
                kept = True
                break
        if not kept:
            print(f"k10={k10:02x} x2mask={x2mask:x} -> drop")

    confirmed = []
    for x2mask, k15 in unknowns:
        res = check_tuple(p, c, leak, k10, x2mask, k15, 5000)
        print(f"recheck k10={k10:02x} x2mask={x2mask:x} k15={k15:02x} -> {res}")
        if res != z3.unsat:
            confirmed.append((x2mask, k15, str(res)))

    print(f"SUMMARY k10={k10:02x} confirmed={confirmed}")


if __name__ == "__main__":
    main()
