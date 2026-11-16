"""Method A: static analysis of the V2 migration.

Two linters are run on every scenario:
  * django-migration-linter (lintmigrations) -> backward-incompatible migration ops
  * Squawk on the PostgreSQL SQL that Django generates for the new migration
A scenario counts as "detected" when a tool reports at least one error/violation
for the new migration. Scenarios without a new migration cannot be analysed.
"""
import json
import re
import subprocess

from common import Timer, build_v2, manage, save
from scenarios import SCENARIOS


# Squawk rules whose documented risk is breaking existing clients / readers (data compatibility).
# All other rules are about locks, rewrites or style and are reported but not counted.
SQUAWK_COMPAT_RULES = {
    "renaming-column", "renaming-table", "ban-drop-column", "ban-drop-table",
    "adding-required-field", "adding-not-nullable-field", "changing-column-type",
    "ban-drop-not-null", "ban-alter-domain-with-add-constraint",
}


def new_migrations(app_dir):
    return sorted(p.stem for p in (app_dir / "orders" / "migrations").glob("0*.py") if not p.stem.startswith("0001"))


def run_django_linter(app_dir):
    proc = manage(app_dir, "lintmigrations", "--include-apps", "orders", "--no-cache")
    out = proc.stdout + proc.stderr
    lines = [l for l in out.splitlines() if "orders" in l and "0001_initial" not in l]
    errors = [l.strip() for l in lines if "ERR" in l]
    warnings = [l.strip() for l in lines if "WARNING" in l]
    # Reasons are printed on the indented lines after an ERR line
    reasons = [l.strip() for l in out.splitlines() if l.startswith("\t") or l.startswith("    ")]
    return {"errors": errors, "warnings": warnings, "reasons": reasons, "raw": out[-3000:]}


def run_squawk(app_dir, migration):
    sql = manage(app_dir, "sqlmigrate", "orders", migration, check=True).stdout
    sql_file = app_dir / f"_{migration}.sql"
    sql_file.write_text(sql, encoding="utf-8")
    proc = subprocess.run(["squawk", "--reporter", "json", str(sql_file)], capture_output=True, text=True)
    try:
        violations = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        violations = [{"rule_name": "parse-output", "message": proc.stdout[-500:] + proc.stderr[-500:]}]
    rules = sorted({v.get("rule_name") for v in violations})
    compat = [r for r in rules if r in SQUAWK_COMPAT_RULES]
    return {"sql": sql.strip(), "rules": rules, "compat_rules": compat}


def main():
    rows = []
    for s in SCENARIOS:
        app_v2 = build_v2(s)
        with Timer() as t:
            migs = new_migrations(app_v2)
            if not migs:
                dj = {"errors": [], "warnings": [], "reasons": [], "raw": "no new migration"}
                sq = {"sql": "", "rules": [], "compat_rules": []}
            else:
                dj = run_django_linter(app_v2)
                sq = run_squawk(app_v2, migs[0])
        row = {
            "scenario": s["id"], "category": s["category"], "truth": s["rollback_incompatible"],
            "new_migration": migs[0] if migs else None,
            "django_linter_detected": bool(dj["errors"]),
            "squawk_detected": bool(sq["compat_rules"]),
            "squawk_any_rule": bool(sq["rules"]),
            "django_linter": dj, "squawk": sq, "seconds": round(t.seconds, 2),
        }
        row["A_detected"] = row["django_linter_detected"] or row["squawk_detected"]
        rows.append(row)
        print(f"{s['id']:<24} truth={s['rollback_incompatible']!s:<5} "
              f"django-linter={row['django_linter_detected']!s:<5} squawk={sq['rules']} compat={sq['compat_rules']} ({t.seconds:.1f}s)")
    save("A_static.json", rows)


if __name__ == "__main__":
    main()
