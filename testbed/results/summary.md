# Measurement results (2026-11-16)

Testbed: Django 5.2 order app, PostgreSQL 16, 8 seeded V2 changes (7 rollback-incompatible, 1 safe control).
Ground truth confirmed for every scenario with a witness input (results/ground_truth.json).

## Per scenario

| Scenario | Category | Incompatible | A1 django-migration-linter | A2 Squawk | A = A1 or A2 | B fixed-data rollback | C = A + B | B failing steps |
|---|---|---|---|---|---|---|---|---|
| S0_safe_add_nullable | control | no | no | no | no | no | no | - |
| S1_enum_new_value | value_range | **yes** | no | no | no | no | no | - |
| S2_nullable_address | null_absent | **yes** | no | **yes** | **yes** | no | **yes** | - |
| S3_phone_e164 | format_requirement | **yes** | no | no | no | **yes** | **yes** | edit, value |
| S4_amount_in_kurus | semantic | **yes** | no | no | no | **yes** | **yes** | value |
| S5_coupon_longer | value_range | **yes** | **yes** | **yes** | **yes** | no | **yes** | - |
| S6_currency_not_null | schema_structure | **yes** | **yes** | no | **yes** | **yes** | **yes** | create |
| S7_rename_note | schema_structure | **yes** | **yes** | **yes** | **yes** | **yes** | **yes** | create, list, read |

## Summary

| Method | Detected (TP) | Missed (FN) | False positive | Detection rate | Total time (s) |
|---|---|---|---|---|---|
| A1 django-migration-linter | 3 | 4 | 0 | 3/7 (43%) | (in A) |
| A2 Squawk | 3 | 4 | 0 | 3/7 (43%) | (in A) |
| A static (A1 or A2) | 4 | 3 | 0 | 4/7 (57%) | 6.9 |
| B fixed-data rollback test | 4 | 3 | 0 | 4/7 (57%) | 32.6 |
| C = A + B | 6 | 1 | 0 | 6/7 (86%) | 39.5 |

## Method R: random, schema-based (Hypothesis), 20 generated inputs per run, 10 seeds

R is counted as detected when the majority of seeds detect the problem.

| Scenario | Incompatible | Seeds detecting | Mean first detecting input | Mean inputs rejected by V2 | Time per run (s) |
|---|---|---|---|---|---|
| S0_safe_add_nullable | no | 0/10 | - | 0/20 | 7.4 |
| S1_enum_new_value | **yes** | 10/10 | 7.3 | 0/20 | 6.8 |
| S2_nullable_address | **yes** | 10/10 | 1 | 0/20 | 7.3 |
| S3_phone_e164 | **yes** | 10/10 | 1 | 0/20 | 7.1 |
| S4_amount_in_kurus | **yes** | 10/10 | 3 | 0/20 | 7.5 |
| S5_coupon_longer | **yes** | 7/10 | 6.7 | 0/20 | 6.9 |
| S6_currency_not_null | **yes** | 10/10 | 1 | 0/20 | 7.2 |
| S7_rename_note | **yes** | 10/10 | 1 | 0/20 | 6.6 |

R summary: detected (majority) 7/7, false positive 0, mean per-seed detection rate on incompatible scenarios 96%, control scenario flagged in 0/10 seeds, total time 568 s.

## Method P: change-aware data generation (proposed)

Deterministic: one run per scenario. Inputs are generated only for the elements whose digest changed.

| Scenario | Incompatible | Change types found | Inputs generated | First detecting input | Detected | Rejected by V2 | Analysis (s) | Total (s) |
|---|---|---|---|---|---|---|---|---|
| S0_safe_add_nullable | no | code_change, structural_add_nullable | 2 | - | no | 0 | 2.0 | 6.2 |
| S1_enum_new_value | **yes** | value_range_choices | 1 | 1 | **yes** | 0 | 1.7 | 6.7 |
| S2_nullable_address | **yes** | code_change, null_absent | 3 | 1 | **yes** | 0 | 2.1 | 6.6 |
| S3_phone_e164 | **yes** | code_change, format | 2 | 1 | **yes** | 0 | 2.6 | 6.5 |
| S4_amount_in_kurus | **yes** | code_change | 1 | 1 | **yes** | 0 | 2.0 | 5.7 |
| S5_coupon_longer | **yes** | value_range_length | 2 | 1 | **yes** | 0 | 1.7 | 5.5 |
| S6_currency_not_null | **yes** | code_change, structural_add_not_null | 2 | 1 | **yes** | 0 | 1.9 | 6.2 |
| S7_rename_note | **yes** | code_change, structural_add_not_null, structural_remove | 1 | 1 | **yes** | 0 | 1.3 | 5.0 |

P summary: detected 7/7, false positive 0, inputs written by V2 per scenario 1-3 (total 14), mean first detecting input 1.0, total time 48 s.

Ablation (P without tracking service/view code, contract fields only): detected 6/7, missed: S4_amount_in_kurus, false positive: none.

## Comparison of all methods

| Method | Detected | False positive | Inputs written by V2 per scenario | Deterministic | Total time (s) |
|---|---|---|---|---|---|
| A static | 4/7 | 0 | 0 (no run) | yes | 7 |
| B fixed data | 4/7 | 0 | 3 | yes | 33 |
| C = A + B | 6/7 | 0 | 3 | yes | 40 |
| R random (20 inputs x 10 seeds) | 7/7 | 0 | 20 | no | 568 |
| P change-aware | 7/7 | 0 | 1-3 | yes | 48 |

Missed even by C: S1_enum_new_value
