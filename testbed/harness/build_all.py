from common import build_v2
from suite import SCENARIOS

if __name__ == "__main__":
    for s in SCENARIOS:
        d = build_v2(s)
        migs = sorted(p.name for p in (d / "orders" / "migrations").glob("0*.py"))
        print(f"{s['id']:<24} migrations={migs}")
