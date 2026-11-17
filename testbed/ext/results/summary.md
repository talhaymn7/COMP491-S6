# Measurement results (2026-11-17)

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
| A static (A1 or A2) | 3 | 5 | 1 | 3/8 (38%) | 11.7 |
| B fixed-data rollback test | 2 | 6 | 0 | 2/8 (25%) | 64.6 |
| C = A + B | 4 | 4 | 1 | 4/8 (50%) | 76.3 |

## Method R: random, schema-based (Hypothesis), 20 generated inputs per run, 10 seeds

R is counted as detected when the majority of seeds detect the problem.

| Scenario | Incompatible | Seeds detecting | Mean first detecting input | Mean inputs rejected by V2 | Time per run (s) |
|---|---|---|---|---|---|
| X0_product_barcode | no | 0/10 | - | 2.8/20 | 9.3 |
| X1_product_name_shorter | no | 0/10 | - | 3/20 | 9.0 |
| X2_order_gift_wrap | no | 0/10 | - | 3.8/20 | 9.0 |
| X3_category_removed | no | 0/10 | - | 3/20 | 9.3 |
| E1_birth_year_range | **yes** | 1/10 | 4 | 3/20 | 9.0 |
| E2_new_carrier | **yes** | 4/10 | 5.5 | 3/20 | 9.3 |
| E3_price_with_vat | **yes** | 10/10 | 6.1 | 3/20 | 9.1 |
| E4_coupon_rule_relaxed | **yes** | 3/10 | 16.7 | 2/20 | 9.0 |
| E5_release_category_city | **yes** | 5/10 | 6.4 | 3/20 | 9.1 |
| E6_sku_longer_digits | **yes** | 9/10 | 9.3 | 3.5/20 | 9.2 |
| E7_tracking_nullable | **yes** | 9/10 | 5.2 | 3.4/20 | 9.3 |
| E8_split_full_name | **yes** | 10/10 | 1 | 7.4/20 | 9.3 |

R summary: detected (majority) 5/8, false positive 0, mean per-seed detection rate on incompatible scenarios 64%, control scenario flagged in 0/40 seeds, total time 1097 s.

## Method P: change-aware data generation (proposed)

Deterministic: one run per scenario. Inputs are generated only for the elements whose digest changed.

| Scenario | Incompatible | Change types found | Inputs generated | First detecting input | Detected | Rejected by V2 | Analysis (s) | Total (s) |
|---|---|---|---|---|---|---|---|---|
| X0_product_barcode | no | code_change, structural_add_nullable | 5 | - | no | 0 | 2.7 | 8.0 |
| X1_product_name_shorter | no | other_field_change | 1 | - | no | 0 | 2.6 | 8.0 |
| X2_order_gift_wrap | no | code_change, structural_add_nullable | 5 | - | no | 0 | 2.7 | 8.1 |
| X3_category_removed | no | other_field_change | 1 | - | no | 0 | 2.8 | 8.1 |
| E1_birth_year_range | **yes** |  | 0 | - | no | 0 | 2.7 | 8.3 |
| E2_new_carrier | **yes** | value_range_choices | 1 | 1 | **yes** | 0 | 3.5 | 9.8 |
| E3_price_with_vat | **yes** | code_change | 4 | 3 | **yes** | 0 | 2.9 | 8.8 |
| E4_coupon_rule_relaxed | **yes** | code_change | 4 | - | no | 0 | 3.1 | 9.3 |
| E5_release_category_city | **yes** | value_range_choices, value_range_length | 3 | 1 | **yes** | 0 | 3.1 | 8.7 |
| E6_sku_longer_digits | **yes** | format | 1 | 1 | **yes** | 0 | 3.1 | 8.6 |
| E7_tracking_nullable | **yes** | code_change, null_absent | 6 | 1 | **yes** | 0 | 3.1 | 12.3 |
| E8_split_full_name | **yes** | code_change, structural_add_not_null, structural_remove | 6 | 1 | **yes** | 0 | 4.4 | 10.6 |

P summary: detected 6/8, false positive 0, inputs written by V2 per scenario 0-6 (total 37), mean first detecting input (detected scenarios) 1.3, total time 109 s.

Manifest integrity (Merkle tree, RFC 6962 hashing; Ed25519 signature): leaves per version 37-39, changed leaves per scenario 1-5, inclusion proof length 3-6 hashes, all proofs verified: True, modified manifest rejected 12/12, modified signature rejected 12/12, mean sign 0.32 ms and verify 0.33 ms per scenario (two manifests).

Ablation (P without tracking service/view code, contract fields only): detected 5/8, missed: E1_birth_year_range, E3_price_with_vat, E4_coupon_rule_relaxed, false positive: none.

## Method B': django-test-migrations (existing tool, used as designed)

Same fixed data as B; forward migration, then reverse migration (schema rollback), rows checked with the V1 historical models. Application code is not executed.

| Scenario | Incompatible | Detected | Failing steps | Note |
|---|---|---|---|---|
| X0_product_barcode | no | no | - |  |
| X1_product_name_shorter | no | no | - |  |
| X2_order_gift_wrap | no | no | - |  |
| X3_category_removed | no | no | - |  |
| E1_birth_year_range | **yes** | no | - |  |
| E2_new_carrier | **yes** | no | - |  |
| E3_price_with_vat | **yes** | no | - | no new migration |
| E4_coupon_rule_relaxed | **yes** | no | - | no new migration |
| E5_release_category_city | **yes** | no | - |  |
| E6_sku_longer_digits | **yes** | no | - |  |
| E7_tracking_nullable | **yes** | no | - |  |
| E8_split_full_name | **yes** | **yes** | reverse_migration |  |

B' summary: detected 1/8, false positive 0, total time 43 s.

Sanity check (witness input added to the V2 data, not a method result): detected 6/8 (E1_birth_year_range, E2_new_carrier, E5_release_category_city, E6_sku_longer_digits, E7_tracking_nullable, E8_split_full_name), false positive: none.

## Comparison of all methods

| Method | Detected | False positive | Inputs written by V2 per scenario | Deterministic | Total time (s) |
|---|---|---|---|---|---|
| A static | 3/8 | 1 | 0 (no run) | yes | 12 |
| B fixed data | 2/8 | 0 | 8 | yes | 65 |
| B' django-test-migrations | 1/8 | 0 | 8 | yes | 43 |
| C = A + B | 4/8 | 1 | 8 | yes | 76 |
| R random (20 inputs x 10 seeds) | 5/8 | 0 | 20 | no | 1097 |
| P change-aware | 6/8 | 0 | 0-6 | yes | 109 |

Missed even by C: E1_birth_year_range, E2_new_carrier, E4_coupon_rule_relaxed, E6_sku_longer_digits
