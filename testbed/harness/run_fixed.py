"""Method B: fixed-data rollback test (V1 -> V2 -> V1 on one PostgreSQL database).

1. V1 creates the schema and writes the fixed data set (pre-upgrade data).
2. Upgrade: V2 migrations run, then V2 writes the SAME fixed data set
   (this is the hand-written regression scenario a team would normally have).
3. Rollback: the V1 code runs again on the V2 database (schema is NOT rolled back)
   and the V1 probe checks read / value / edit / create / report behaviour.
A scenario counts as "detected" when the probe reports at least one finding.
"""
import json

from common import RESULTS, V1_DIR, Timer, build_v2, fresh_db, manage, save
from scenarios import SCENARIOS

FIXED_INPUTS = [
    {"customer_name": "Ayse Yilmaz", "phone": "05321112233", "status": "pending",
     "shipping_address": "Talas, Kayseri", "coupon_code": "", "total_tl": 250},
    {"customer_name": "Mehmet Demir", "phone": "05559998877", "status": "paid",
     "shipping_address": "Cankaya, Ankara", "coupon_code": "YAZ10", "total_tl": 1200},
    {"customer_name": "Zeynep Kaya", "phone": "05061234567", "status": "shipped",
     "shipping_address": "Kadikoy, Istanbul", "coupon_code": "", "total_tl": 75},
]


def rollback_cycle(scenario, inputs_v1, inputs_v2, tag):
    """Run V1 -> V2 -> V1 and return the V1 probe report."""
    app_v2 = build_v2(scenario)
    work = RESULTS / "work" / tag / scenario["id"]
    work.mkdir(parents=True, exist_ok=True)
    db = fresh_db(f"rb_{tag}_{scenario['id'].split('_')[0].lower()}")
    timings = {}

    with Timer() as t:
        manage(V1_DIR, "migrate", "--noinput", db=db, check=True)
        (work / "in_v1.json").write_text(json.dumps(inputs_v1), encoding="utf-8")
        manage(V1_DIR, "drive", "--inputs", str(work / "in_v1.json"), "--out", str(work / "out_v1.json"), db=db, check=True)
    timings["v1_seed"] = t.seconds

    with Timer() as t:
        manage(app_v2, "migrate", "--noinput", db=db, check=True)
        (work / "in_v2.json").write_text(json.dumps(inputs_v2), encoding="utf-8")
        manage(app_v2, "drive", "--inputs", str(work / "in_v2.json"), "--out", str(work / "out_v2.json"), db=db, check=True)
    timings["v2_upgrade_and_write"] = t.seconds

    written = json.loads((work / "out_v1.json").read_text(encoding="utf-8")) + \
        json.loads((work / "out_v2.json").read_text(encoding="utf-8"))
    expect = [{"id": w["id"], "input": w["input"]} for w in written if w["id"]]
    (work / "expect.json").write_text(json.dumps(expect), encoding="utf-8")

    with Timer() as t:
        manage(V1_DIR, "probe", "--expect", str(work / "expect.json"), "--out", str(work / "probe.json"), db=db, check=True)
    timings["v1_rollback_probe"] = t.seconds

    probe = json.loads((work / "probe.json").read_text(encoding="utf-8"))
    rejected_by_v2 = [w for w in written if not w["id"]]
    return probe, rejected_by_v2, timings


def main():
    rows = []
    for s in SCENARIOS:
        with Timer() as t:
            probe, rejected, timings = rollback_cycle(s, FIXED_INPUTS, FIXED_INPUTS, "B")
        f = probe["findings"]
        row = {
            "scenario": s["id"], "category": s["category"], "truth": s["rollback_incompatible"],
            "B_detected": bool(f), "n_findings": len(f),
            "finding_steps": sorted({x["step"] for x in f}),
            "findings": f[:10], "orders_checked": probe["orders_checked"],
            "inputs_rejected_by_v2": len(rejected), "tests_executed": len(FIXED_INPUTS) * 2,
            "timings": {k: round(v, 2) for k, v in timings.items()}, "seconds": round(t.seconds, 2),
        }
        rows.append(row)
        first = f[0]["error"][:90] if f else "-"
        print(f"{s['id']:<24} truth={s['rollback_incompatible']!s:<5} detected={row['B_detected']!s:<5} "
              f"steps={row['finding_steps']} ({t.seconds:.1f}s) {first}")
    save("B_fixed.json", rows)


if __name__ == "__main__":
    main()
