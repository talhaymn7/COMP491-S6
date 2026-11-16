"""Ground-truth check: for each scenario, one hand-written witness input that V2
accepts. If the scenario is rollback-incompatible, the V1 probe must report a
finding; for the control scenario it must stay clean. This validates the labels
in scenarios.py before methods are compared against them."""
from common import Timer, save
from run_fixed import FIXED_INPUTS, rollback_cycle
from scenarios import SCENARIOS

BASE = dict(FIXED_INPUTS[0])
WITNESS = {
    "S0_safe_add_nullable": {**BASE, "gift_message": "Iyi ki dogdun"},
    "S1_enum_new_value": {**BASE, "status": "partially_shipped"},
    "S2_nullable_address": {**BASE, "shipping_address": None},
    "S3_phone_e164": BASE,
    "S4_amount_in_kurus": BASE,
    "S5_coupon_longer": {**BASE, "coupon_code": "BLACKFRIDAY2026"},
    "S6_currency_not_null": BASE,
    "S7_rename_note": BASE,
}


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
