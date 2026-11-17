"""Combine results/*.json into results/summary.md (methods A, B and C = A + B)."""
import json
from datetime import date

from common import RESULTS
from suite import DESCRIPTION, FIXED_INPUTS


def load(name):
    with open(RESULTS / name, encoding="utf-8") as f:
        return {r["scenario"]: r for r in json.load(f)}


def metrics(rows, key):
    tp = sum(1 for r in rows if r["truth"] and r[key])
    fn = sum(1 for r in rows if r["truth"] and not r[key])
    fp = sum(1 for r in rows if not r["truth"] and r[key])
    pos = tp + fn
    return tp, fn, fp, pos


def yn(v):
    return "**yes**" if v else "no"


def main():
    A, B = load("A_static.json"), load("B_fixed.json")
    truth = load("ground_truth.json")
    R = load("R_random.json") if (RESULTS / "R_random.json").exists() else {}
    rows = []
    for sid, a in A.items():
        b = B[sid]
        rows.append({
            "scenario": sid, "category": a["category"], "truth": a["truth"],
            "label_confirmed": truth[sid]["label_confirmed"],
            "A1": a["django_linter_detected"], "A2": a["squawk_detected"], "A": a["A_detected"],
            "B": b["B_detected"], "C": a["A_detected"] or b["B_detected"],
            "A_s": a["seconds"], "B_s": b["seconds"], "B_steps": ", ".join(b["finding_steps"]) or "-",
        })
        if R:
            r = R[sid]
            rows[-1].update({"R": r["R_detected"], "R_rate": r["R_detection_rate"],
                             "R_first": r["mean_first_detecting_input"], "R_rej": r["mean_rejected_by_v2"],
                             "R_s": r["seconds"], "R_budget": r["budget"], "R_seeds": r["seeds"]})

    lines = [f"# Measurement results ({date.today().isoformat()})", "",
             DESCRIPTION,
             "Ground truth confirmed for every scenario with a witness input (results/ground_truth.json).", "",
             "## Per scenario", "",
             "| Scenario | Category | Incompatible | A1 django-migration-linter | A2 Squawk | A = A1 or A2 | B fixed-data rollback | C = A + B | B failing steps |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['scenario']} | {r['category']} | {yn(r['truth'])} | {yn(r['A1'])} | {yn(r['A2'])} | "
                     f"{yn(r['A'])} | {yn(r['B'])} | {yn(r['C'])} | {r['B_steps']} |")

    lines += ["", "## Summary", "",
              "| Method | Detected (TP) | Missed (FN) | False positive | Detection rate | Total time (s) |",
              "|---|---|---|---|---|---|"]
    totals = {"A1": sum(r["A_s"] for r in rows), "A2": sum(r["A_s"] for r in rows), "A": sum(r["A_s"] for r in rows),
              "B": sum(r["B_s"] for r in rows)}
    totals["C"] = totals["A"] + totals["B"]
    names = {"A1": "A1 django-migration-linter", "A2": "A2 Squawk", "A": "A static (A1 or A2)",
             "B": "B fixed-data rollback test", "C": "C = A + B"}
    for k, label in names.items():
        tp, fn, fp, pos = metrics(rows, k)
        t = f"{totals[k]:.1f}" if k not in ("A1", "A2") else "(in A)"
        lines.append(f"| {label} | {tp} | {fn} | {fp} | {tp}/{pos} ({100 * tp / pos:.0f}%) | {t} |")

    if R:
        r0 = rows[0]
        lines += ["", f"## Method R: random, schema-based (Hypothesis), {r0['R_budget']} generated inputs per run, "
                  f"{r0['R_seeds']} seeds", "",
                  "R is counted as detected when the majority of seeds detect the problem.", "",
                  "| Scenario | Incompatible | Seeds detecting | Mean first detecting input | Mean inputs rejected by V2 | Time per run (s) |",
                  "|---|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['scenario']} | {yn(r['truth'])} | {round(r['R_rate'] * r['R_seeds'])}/{r['R_seeds']} | "
                         f"{r['R_first'] if r['R_first'] is not None else '-'} | {r['R_rej']}/{r['R_budget']} | {r['R_s']:.1f} |")
        tp, fn, fp, pos = metrics(rows, "R")
        inc = [r for r in rows if r["truth"]]
        mean_rate = sum(r["R_rate"] for r in inc) / len(inc)
        ctl = [r for r in rows if not r["truth"]]
        lines += ["", f"R summary: detected (majority) {tp}/{pos}, false positive {fp}, "
                  f"mean per-seed detection rate on incompatible scenarios {100 * mean_rate:.0f}%, "
                  f"control scenario flagged in {sum(round(r['R_rate'] * r['R_seeds']) for r in ctl)}"
                  f"/{sum(r['R_seeds'] for r in ctl)} seeds, total time {sum(r['R_s'] * r['R_seeds'] for r in rows):.0f} s."]

    P = load("P_change_aware.json") if (RESULTS / "P_change_aware.json").exists() else {}
    PN = load("P_change_aware_nocode.json") if (RESULTS / "P_change_aware_nocode.json").exists() else {}
    if P:
        lines += ["", "## Method P: change-aware data generation (proposed)", "",
                  "Deterministic: one run per scenario. Inputs are generated only for the elements whose digest changed.", "",
                  "| Scenario | Incompatible | Change types found | Inputs generated | First detecting input | Detected | Rejected by V2 | Analysis (s) | Total (s) |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            p = P[r["scenario"]]
            r["P"] = p["P_detected"]
            lines.append(f"| {r['scenario']} | {yn(r['truth'])} | {', '.join(p['change_types'])} | {p['inputs_generated']} | "
                         f"{p['first_detecting_input'] or '-'} | {yn(p['P_detected'])} | {p['rejected_by_v2']} | "
                         f"{p['seconds_analysis']:.1f} | {p['seconds']:.1f} |")
        tp, fn, fp, pos = metrics(rows, "P")
        inc = [P[r["scenario"]] for r in rows if r["truth"]]
        lines += ["", f"P summary: detected {tp}/{pos}, false positive {fp}, "
                  f"inputs written by V2 per scenario {min(p['inputs_generated'] for p in P.values())}-"
                  f"{max(p['inputs_generated'] for p in P.values())} "
                  f"(total {sum(p['inputs_generated'] for p in P.values())}), "
                  f"mean first detecting input (detected scenarios) "
                  f"{sum(p['first_detecting_input'] for p in inc if p['P_detected']) / max(1, sum(1 for p in inc if p['P_detected'])):.1f}, "
                  f"total time {sum(p['seconds'] for p in P.values()):.0f} s."]
        I = [p["integrity"] for p in P.values() if p.get("integrity")]
        if I:
            n_t = len(I)
            lines += ["", "Manifest integrity (Merkle tree, RFC 6962 hashing; Ed25519 signature): "
                      f"leaves per version {min(i['leaves_v2'] for i in I)}-{max(i['leaves_v2'] for i in I)}, "
                      f"changed leaves per scenario {min(len(i['changed_leaves']) for i in I)}-"
                      f"{max(len(i['changed_leaves']) for i in I)}, inclusion proof length "
                      f"{min(min(i['proof_hashes'] or [0]) for i in I)}-{max(max(i['proof_hashes'] or [0]) for i in I)} hashes, "
                      f"all proofs verified: {all(i['proofs_verified'] for i in I)}, "
                      f"modified manifest rejected {sum(i['tamper']['modified_manifest_rejected'] for i in I)}/{n_t}, "
                      f"modified signature rejected {sum(i['tamper']['modified_signature_rejected'] for i in I)}/{n_t}, "
                      f"mean sign {sum(i['ms_sign'] for i in I) / n_t:.2f} ms and verify {sum(i['ms_verify'] for i in I) / n_t:.2f} ms "
                      "per scenario (two manifests)."]
        if PN:
            missed =[s for s, p in PN.items() if p["truth"] and not p["P_detected"]]
            fpn = [s for s, p in PN.items() if not p["truth"] and p["P_detected"]]
            lines += ["", "Ablation (P without tracking service/view code, contract fields only): "
                      f"detected {sum(1 for p in PN.values() if p['truth'] and p['P_detected'])}/{pos}, "
                      f"missed: {', '.join(missed) or 'none'}, false positive: {', '.join(fpn) or 'none'}."]

        BD = load("Bdtm_django_test_migrations.json") if (RESULTS / "Bdtm_django_test_migrations.json").exists() else {}
        if BD:
            lines += ["", "## Method B': django-test-migrations (existing tool, used as designed)", "",
                      "Same fixed data as B; forward migration, then reverse migration (schema rollback), "
                      "rows checked with the V1 historical models. Application code is not executed.", "",
                      "| Scenario | Incompatible | Detected | Failing steps | Note |", "|---|---|---|---|---|"]
            for r in rows:
                b = BD[r["scenario"]]
                r["BD"] = b["Bdtm_detected"]
                lines.append(f"| {r['scenario']} | {yn(r['truth'])} | {yn(b['Bdtm_detected'])} | "
                             f"{', '.join(b['finding_steps']) or '-'} | {b['not_applicable'] or ''} |")
            tp, fn, fp, pos = metrics(rows, "BD")
            lines += ["", f"B' summary: detected {tp}/{pos}, false positive {fp}, "
                      f"total time {sum(b['seconds'] for b in BD.values()):.0f} s."]
            if (RESULTS / "Bdtm_witness_sanity.json").exists():
                W = load("Bdtm_witness_sanity.json")
                hit = sorted(s for s, w in W.items() if w["truth"] and w["Bdtm_detected"])
                fpw = sorted(s for s, w in W.items() if not w["truth"] and w["Bdtm_detected"])
                lines += ["", "Sanity check (witness input added to the V2 data, not a method result): "
                          f"detected {len(hit)}/{pos} ({', '.join(hit)}), false positive: {', '.join(fpw) or 'none'}."]

        lines += ["", "## Comparison of all methods", "",
                  "| Method | Detected | False positive | Inputs written by V2 per scenario | Deterministic | Total time (s) |",
                  "|---|---|---|---|---|---|"]
        tA = sum(r["A_s"] for r in rows); tB = sum(r["B_s"] for r in rows)
        for key, label, inputs, det, t in [
            ("A", "A static", "0 (no run)", "yes", tA), ("B", "B fixed data", str(len(FIXED_INPUTS)), "yes", tB),
            ("BD", "B' django-test-migrations", str(len(FIXED_INPUTS)), "yes",
             sum(b["seconds"] for b in BD.values()) if BD else 0),
            ("C", "C = A + B", str(len(FIXED_INPUTS)), "yes", tA + tB),
            ("R", f"R random ({r0['R_budget']} inputs x {r0['R_seeds']} seeds)", str(r0["R_budget"]), "no",
             sum(r["R_s"] * r["R_seeds"] for r in rows) if R else 0),
            ("P", "P change-aware", f"{min(p['inputs_generated'] for p in P.values())}-"
             f"{max(p['inputs_generated'] for p in P.values())}", "yes", sum(p["seconds"] for p in P.values())),
        ]:
            if (key == "R" and not R) or (key == "BD" and not BD):
                continue
            tp, fn, fp, pos = metrics(rows, key)
            lines.append(f"| {label} | {tp}/{pos} | {fp} | {inputs} | {det} | {t:.0f} |")

    missed_c = [r["scenario"] for r in rows if r["truth"] and not r["C"]]
    lines += ["", f"Missed even by C: {', '.join(missed_c) or 'none'}", ""]
    (RESULTS / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
