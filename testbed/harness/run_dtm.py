"""Method B': the existing tool django-test-migrations, used as designed.

Same fixed data as method B, but the tool tests the migration scripts: data is written
at the V1 and V2 migration states with historical models, the V2 migration is reversed
(schema rollback) and the rows are checked with the V1 historical models. Application
code is not executed. Scenarios without a new migration cannot be tested by the tool.
A scenario counts as "detected" when the check reports at least one finding.
"""
import json
import os

from common import RESULTS, Timer, build_v2, fresh_db, manage, save
from suite import FIXED_INPUTS, SCENARIOS, WITNESS

# Sanity check: DTM_WITNESS=1 adds the witness input of each scenario to the data written at the V2 state,
# to confirm that the assertions can fire when the data contains the new values.
WITH_WITNESS = os.environ.get("DTM_WITNESS") == "1"


def migrations(app_dir):
    return sorted(p.stem for p in (app_dir / "orders" / "migrations").glob("0*.py"))


def main():
    rows = []
    for s in SCENARIOS:
        with Timer() as t:
            app_v2 = build_v2(s)
            migs = migrations(app_v2)
            work = RESULTS / "work" / ("Bdtm_witness" if WITH_WITNESS else "Bdtm") / s["id"]
            work.mkdir(parents=True, exist_ok=True)
            if len(migs) < 2:
                report = {"rows": 0, "findings": [], "not_applicable": "no new migration"}
            else:
                db = fresh_db(f"rb_dtm{'w' if WITH_WITNESS else ''}_{s['id'].split('_')[0].lower()}")
                # create Django's migration table (nothing applied yet), as a test database would have
                manage(app_v2, "migrate", "contenttypes", "--noinput", db=db, check=True)
                inputs_v2 = FIXED_INPUTS + ([WITNESS[s["id"]]] if WITH_WITNESS else [])
                (work / "inputs.json").write_text(json.dumps(FIXED_INPUTS), encoding="utf-8")
                (work / "inputs_v2.json").write_text(json.dumps(inputs_v2), encoding="utf-8")
                manage(app_v2, "dtm_check", "--inputs", str(work / "inputs.json"),
                       "--inputs-v2", str(work / "inputs_v2.json"), "--v1", migs[0],
                       "--v2", migs[-1], "--out", str(work / "dtm.json"), db=db, check=True)
                report = json.loads((work / "dtm.json").read_text(encoding="utf-8"))
        f = report["findings"]
        if any(x["step"] == "error" for x in f):
            raise RuntimeError(f"{s['id']}: django-test-migrations setup error: {f}")
        row = {
            "scenario": s["id"], "category": s["category"], "truth": s["rollback_incompatible"],
            "Bdtm_detected": bool(f), "not_applicable": report.get("not_applicable"),
            "finding_steps": sorted({x["step"] for x in f}), "findings": f[:10],
            "seconds": round(t.seconds, 2),
        }
        rows.append(row)
        first = f[0]["error"][:90] if f else (report.get("not_applicable") or "-")
        print(f"{s['id']:<24} truth={s['rollback_incompatible']!s:<5} detected={row['Bdtm_detected']!s:<5} "
              f"steps={row['finding_steps']} ({t.seconds:.1f}s) {first}")
    save("Bdtm_witness_sanity.json" if WITH_WITNESS else "Bdtm_django_test_migrations.json", rows)


if __name__ == "__main__":
    main()
