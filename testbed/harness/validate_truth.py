"""Ground-truth check: for each scenario, one hand-written witness input that V2
accepts. If the scenario is rollback-incompatible, the V1 probe must report a
finding; for the control scenario it must stay clean. This validates the labels
in scenarios.py before methods are compared against them."""
from common import Timer, save
from run_fixed import rollback_cycle
from suite import SCENARIOS, WITNESS



def main():
    rows = []
    for s in SCENARIOS:
        with Timer() as t:
            probe, rejected, _ = rollback_cycle(s, [], [WITNESS[s["id"]]], "truth")
        detected = bool(probe["findings"])
        ok = (detected == s["rollback_incompatible"]) and not rejected
        rows.append({"scenario": s["id"], "truth": s["rollback_incompatible"], "witness_detected": detected,
                     "accepted_by_v2": not rejected, "label_confirmed": ok, "findings": probe["findings"][:5]})
        first = probe["findings"][0]["error"][:90] if probe["findings"] else "-"
        print(f"{s['id']:<24} truth={s['rollback_incompatible']!s:<5} witness_detected={detected!s:<5} "
              f"v2_accepted={not rejected!s:<5} confirmed={ok} {first}")
    save("ground_truth.json", rows)


if __name__ == "__main__":
    main()
