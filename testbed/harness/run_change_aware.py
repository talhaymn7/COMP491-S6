"""Method P: change-aware data generation (the proposed approach).

1. Digest manifest: for V1 and V2, SHA-256 digests of the data-defining artifacts
   (models, services, views and migration files, hashed in a normalized form: the
   Python syntax tree, so formatting and comments do not change a digest) and of a
   normalized descriptor of every model field (data contract).
2. Diff + classification: fields whose digest changed are mapped to change types
   (value range, null/absent, format, structural); changed code artifacts without a
   field change are classified as code changes (possible semantic change).
3. Targeted generation: small inputs only for the changed elements, built on one
   typical record (the first fixed input of method B).
4. Execution: the same V1 -> V2 -> V1 cycle and the same V1 probe as B and R.

Signing of the manifest (e.g. with Sigstore) is not performed in the testbed; the
SHA-256 digest of each manifest is recorded instead.
"""
import ast
import hashlib
import json
import os
import re

from hypothesis import HealthCheck, find, settings
from hypothesis import strategies as st

from common import RESULTS, V1_DIR, Timer, build_v2, manage, save
from run_fixed import FIXED_INPUTS, rollback_cycle
from run_random import first_detecting_input
from suite import SCENARIOS

# Hand-written part of the contract: how model fields map to the create API.
# (Method R uses the same knowledge in gen_random.py.)
API_SKIP = {"id", "created_at", "note", "customer_note"}
API_NAME = {"total_amount": "total_tl"}
BASE = dict(FIXED_INPUTS[0])  # one typical, valid record
CODE_ARTIFACTS = ["orders/models.py", "orders/services.py", "orders/views.py"]
# Ablation switch: P_TRACK_CODE=0 ignores changes of service/view code (contract fields only).
TRACK_CODE = os.environ.get("P_TRACK_CODE", "1") != "0"
TAG = "P" if TRACK_CODE else "P_nocode"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized(path):
    text = path.read_text(encoding="utf-8")
    try:
        return ast.dump(ast.parse(text), include_attributes=False).encode()
    except SyntaxError:
        return text.encode()


def manifest(app_dir, work, tag):
    out = work / f"contract_{tag}.json"
    manage(app_dir, "describe_contract", "--out", str(out), check=True)
    fields = json.loads(out.read_text(encoding="utf-8"))["fields"]
    migrations = sorted(f"orders/migrations/{p.name}" for p in (app_dir / "orders" / "migrations").glob("0*.py"))
    m = {
        "artifacts": {f: sha256(normalized(app_dir / f)) for f in CODE_ARTIFACTS + migrations},
        "fields": {name: sha256(json.dumps(d, sort_keys=True).encode()) for name, d in fields.items()},
    }
    m["manifest_sha256"] = sha256(json.dumps(m, sort_keys=True).encode())
    (work / f"manifest_{tag}.json").write_text(json.dumps(m, indent=1, sort_keys=True), encoding="utf-8")
    return m, fields


def classify(m1, f1, m2, f2):
    changes = []
    for name in sorted(set(f1) | set(f2)):
        a, b = f1.get(name), f2.get(name)
        if a is None:
            not_null = not b["null"] and not b["db_default"]
            changes.append({"field": name, "type": "structural_add_not_null" if not_null else "structural_add_nullable",
                            "descriptor": b})
            continue
        if b is None:
            changes.append({"field": name, "type": "structural_remove"})
            continue
        if m1["fields"][name] == m2["fields"][name]:
            continue
        found = False
        new_choices = sorted(set(b["choices"] or []) - set(a["choices"] or []))
        if new_choices:
            changes.append({"field": name, "type": "value_range_choices", "values": new_choices}); found = True
        if (a["max_length"] or 0) < (b["max_length"] or 0):
            changes.append({"field": name, "type": "value_range_length",
                            "v1_max": a["max_length"], "v2_max": b["max_length"]}); found = True
        if not a["null"] and b["null"]:
            changes.append({"field": name, "type": "null_absent"}); found = True
        if a["regex"] != b["regex"]:
            changes.append({"field": name, "type": "format", "v1": a["regex"], "v2": b["regex"]}); found = True
        if a["type"] != b["type"] or a["column"] != b["column"]:
            changes.append({"field": name, "type": "structural_type"}); found = True
        if not found:
            changes.append({"field": name, "type": "other_field_change"})
    code = [f for f in ("orders/services.py", "orders/views.py") if m1["artifacts"].get(f) != m2["artifacts"].get(f)]
    if code and TRACK_CODE:
        changes.append({"field": None, "type": "code_change", "files": code})
    new_migrations = sorted(set(m2["artifacts"]) - set(m1["artifacts"]))
    return changes, new_migrations


def fill(n):
    return "P" * n


def format_example(v1_patterns, v2_patterns):
    """Smallest value valid for the V2 format but rejected by the V1 format."""
    if not v2_patterns:
        return "x"
    for pat in v2_patterns:
        try:
            return find(st.from_regex(pat, fullmatch=True),
                        lambda s: not any(re.search(p, s) for p in v1_patterns),
                        settings=settings(database=None, max_examples=2000,
                                          suppress_health_check=list(HealthCheck)))
        except Exception:
            continue
    return None


def generate(changes):
    out = []

    def add(why, override=None, drop=None):
        item = dict(BASE)
        item.update(override or {})
        if drop:
            item.pop(drop, None)
        out.append({"why": why, "input": item})

    for c in changes:
        f, t = c["field"], c["type"]
        name = API_NAME.get(f, f) if f else None
        in_api = f is not None and f not in API_SKIP
        if t == "value_range_choices":
            for v in c["values"]:
                add(f"{f}: value {v!r} unknown to V1", {name: v})
        elif t == "value_range_length":
            add(f"{f}: length {c['v1_max'] + 1} > V1 limit {c['v1_max']}", {name: fill(c["v1_max"] + 1)})
            add(f"{f}: maximum V2 length {c['v2_max']}", {name: fill(c["v2_max"])})
        elif t == "null_absent":
            add(f"{f}: null", {name: None})
            add(f"{f}: absent", drop=name)
        elif t == "format":
            value = format_example(c["v1"], c["v2"])
            if value is not None:
                add(f"{f}: V2 format {value!r} rejected by V1 format", {name: value})
        elif t in ("structural_add_not_null", "structural_add_nullable"):
            if in_api:
                d = c["descriptor"]
                add(f"{f}: new field with a value", {name: fill(min(d["max_length"] or 8, 8))})
                add(f"{f}: new field absent", drop=name)
            else:
                add(f"{f}: new field (not in API), typical record")
        else:  # structural_remove, structural_type, other_field_change, code_change
            add(f"{t} ({f or ', '.join(c.get('files', []))}): typical record with non-zero values")

    seen, unique = set(), []
    for g in out:
        key = json.dumps(g["input"], sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(g)
    return unique


def main():
    rows = []
    for s in SCENARIOS:
        work = RESULTS / "work" / TAG / s["id"]
        work.mkdir(parents=True, exist_ok=True)
        with Timer() as total:
            with Timer() as analysis:
                app_v2 = build_v2(s)
                m1, f1 = manifest(V1_DIR, work, "v1")
                m2, f2 = manifest(app_v2, work, "v2")
                changes, new_migrations = classify(m1, f1, m2, f2)
                generated = generate(changes)
            (work / "generated.json").write_text(json.dumps(generated, ensure_ascii=False, indent=1), encoding="utf-8")
            probe, rejected, timings = rollback_cycle(s, FIXED_INPUTS, [g["input"] for g in generated], TAG)
        written_v2 = json.loads((work / "out_v2.json").read_text(encoding="utf-8"))
        row = {
            "scenario": s["id"], "category": s["category"], "truth": s["rollback_incompatible"],
            "P_detected": bool(probe["findings"]),
            "changes": changes, "change_types": sorted({c["type"] for c in changes}),
            "new_migrations": new_migrations,
            "manifest_v1": m1["manifest_sha256"], "manifest_v2": m2["manifest_sha256"],
            "inputs_generated": len(generated), "why": [g["why"] for g in generated],
            "first_detecting_input": first_detecting_input(probe, written_v2),
            "finding_steps": sorted({x["step"] for x in probe["findings"]}),
            "findings": probe["findings"][:10], "rejected_by_v2": len(rejected),
            "seconds_analysis": round(analysis.seconds, 2), "seconds": round(total.seconds, 2),
        }
        rows.append(row)
        print(f"{s['id']:<24} truth={s['rollback_incompatible']!s:<5} detected={row['P_detected']!s:<5} "
              f"changes={row['change_types']} inputs={len(generated)} first={row['first_detecting_input']} "
              f"rejected={len(rejected)} ({total.seconds:.1f}s, analysis {analysis.seconds:.1f}s)")
    save("P_change_aware.json" if TRACK_CODE else "P_change_aware_nocode.json", rows)


if __name__ == "__main__":
    main()
