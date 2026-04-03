from math import gcd


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


def verify(p: int, q: int, m: int) -> None:
    print("check (p & MASK) == PM:", (p & MASK) == PM)
    print("check p*q == N:", p * q == N)
    print("check gcd(e,phi)==1:", gcd(E, (p - 1) * (q - 1)) == 1)
    print("check m^e mod N == ct:", pow(m, E, N) == CT)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print("Usage: python verify_q7_solution.py <p_hex> <q_hex> <m_hex>")
        raise SystemExit(1)

    p = int(sys.argv[1], 16)
    q = int(sys.argv[2], 16)
    m = int(sys.argv[3], 16)
    verify(p, q, m)
