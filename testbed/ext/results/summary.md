# Measurement results (2026-11-16)

Extended testbed: Django 5.2 app with 4 resources (order, customer, product, shipment), about 30 fields, PostgreSQL 16, 12 seeded V2 changes (8 rollback-incompatible, 4 safe controls).
Ground truth confirmed for every scenario with a witness input (results/ground_truth.json).

## Per scenario

| Scenario | Category | Incompatible | A1 django-migration-linter | A2 Squawk | A = A1 or A2 | B fixed-data rollback | C = A + B | B failing steps |
|---|---|---|---|---|---|---|---|---|
| X0_product_barcode | control | no | no | no | no | no | no | - |
| X1_product_name_shorter | control | no | **yes** | **yes** | **yes** | no | **yes** | - |
| X2_order_gift_wrap | control | no | no | no | no | no | no | - |
| X3_category_removed | control | no | no | no | no | no | no | - |
| E1_birth_year_range | value_range | **yes** | no | no | no | no | no | - |
| E2_new_carrier | value_range | **yes** | no | no | no | no | no | - |
| E3_price_with_vat | semantic | **yes** | no | no | no | **yes** | **yes** | value |
| E4_coupon_rule_relaxed | business_rule | **yes** | no | no | no | no | no | - |
| E5_release_category_city | multi_change | **yes** | **yes** | **yes** | **yes** | no | **yes** | - |
| E6_sku_longer_digits | format_requirement | **yes** | no | no | no | no | no | - |
| E7_tracking_nullable | null_absent | **yes** | no | **yes** | **yes** | no | **yes** | - |
| E8_split_full_name | schema_structure | **yes** | **yes** | **yes** | **yes** | **yes** | **yes** | create, list, read |

## Summary

| Method | Detected (TP) | Missed (FN) | False positive | Detection rate | Total time (s) |
|---|---|---|---|---|---|
| A1 django-migration-linter | 2 | 6 | 1 | 2/8 (25%) | (in A) |
| A2 Squawk | 3 | 5 | 1 | 3/8 (38%) | (in A) |
| A static (A1 or A2) | 3 | 5 | 1 | 3/8 (38%) | 9.0 |
| B fixed-data rollback test | 2 | 6 | 0 | 2/8 (25%) | 42.2 |
| C = A + B | 4 | 4 | 1 | 4/8 (50%) | 51.2 |

## Method R: random, schema-based (Hypothesis), 20 generated inputs per run, 10 seeds

R is counted as detected when the majority of seeds detect the problem.

| Scenario | Incompatible | Seeds detecting | Mean first detecting input | Mean inputs rejected by V2 | Time per run (s) |
|---|---|---|---|---|---|
| X0_product_barcode | no | 0/10 | - | 2.8/20 | 6.3 |
| X1_product_name_shorter | no | 0/10 | - | 3/20 | 6.2 |
| X2_order_gift_wrap | no | 0/10 | - | 3.8/20 | 6.3 |
| X3_category_removed | no | 0/10 | - | 3/20 | 6.2 |
| E1_birth_year_range | **yes** | 1/10 | 4 | 3/20 | 6.2 |
| E2_new_carrier | **yes** | 4/10 | 5.5 | 3/20 | 6.5 |
| E3_price_with_vat | **yes** | 10/10 | 6.1 | 3/20 | 6.6 |
| E4_coupon_rule_relaxed | **yes** | 3/10 | 16.7 | 2/20 | 6.8 |
| E5_release_category_city | **yes** | 5/10 | 6.4 | 3/20 | 7.2 |
| E6_sku_longer_digits | **yes** | 9/10 | 9.3 | 3.5/20 | 6.3 |
| E7_tracking_nullable | **yes** | 9/10 | 5.2 | 3.4/20 | 6.1 |
| E8_split_full_name | **yes** | 10/10 | 1 | 7.4/20 | 6.1 |

R summary: detected (majority) 5/8, false positive 0, mean per-seed detection rate on incompatible scenarios 64%, control scenario flagged in 0/40 seeds, total time 768 s.

## Method P: change-aware data generation (proposed)

Deterministic: one run per scenario. Inputs are generated only for the elements whose digest changed.

| Scenario | Incompatible | Change types found | Inputs generated | First detecting input | Detected | Rejected by V2 | Analysis (s) | Total (s) |
|---|---|---|---|---|---|---|---|---|
| X0_product_barcode | no | code_change, structural_add_nullable | 5 | - | no | 0 | 1.7 | 4.9 |
| X1_product_name_shorter | no | other_field_change | 1 | - | no | 0 | 1.7 | 4.9 |
| X2_order_gift_wrap | no | code_change, structural_add_nullable | 5 | - | no | 0 | 1.7 | 5.0 |
| X3_category_removed | no | other_field_change | 1 | - | no | 0 | 1.9 | 5.0 |
| E1_birth_year_range | **yes** |  | 0 | - | no | 0 | 1.8 | 5.0 |
| E2_new_carrier | **yes** | value_range_choices | 1 | 1 | **yes** | 0 | 2.0 | 5.1 |
| E3_price_with_vat | **yes** | code_change | 4 | 3 | **yes** | 0 | 1.7 | 4.9 |
| E4_coupon_rule_relaxed | **yes** | code_change | 4 | - | no | 0 | 2.0 | 5.1 |
| E5_release_category_city | **yes** | value_range_choices, value_range_length | 3 | 1 | **yes** | 0 | 1.8 | 5.0 |
| E6_sku_longer_digits | **yes** | format | 1 | 1 | **yes** | 0 | 2.0 | 5.2 |
| E7_tracking_nullable | **yes** | code_change, null_absent | 6 | 1 | **yes** | 0 | 1.7 | 5.0 |
| E8_split_full_name | **yes** | code_change, structural_add_not_null, structural_remove | 6 | 1 | **yes** | 0 | 1.6 | 4.7 |

P summary: detected 6/8, false positive 0, inputs written by V2 per scenario 0-6 (total 37), mean first detecting input (detected scenarios) 1.3, total time 60 s.

Ablation (P without tracking service/view code, contract fields only): detected 5/8, missed: E1_birth_year_range, E3_price_with_vat, E4_coupon_rule_relaxed, false positive: none.

## Comparison of all methods

| Method | Detected | False positive | Inputs written by V2 per scenario | Deterministic | Total time (s) |
|---|---|---|---|---|---|
| A static | 3/8 | 1 | 0 (no run) | yes | 9 |
| B fixed data | 2/8 | 0 | 8 | yes | 42 |
| C = A + B | 4/8 | 1 | 8 | yes | 51 |
| R random (20 inputs x 10 seeds) | 5/8 | 0 | 20 | no | 768 |
| P change-aware | 6/8 | 0 | 0-6 | yes | 60 |

Missed even by C: E1_birth_year_range, E2_new_carrier, E4_coupon_rule_relaxed, E6_sku_longer_digits
