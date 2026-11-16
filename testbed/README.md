# Rollback compatibility testbed

Requirements: Docker Desktop (running). Everything else runs in containers.

```bash
docker compose up -d db
docker compose build runner
MSYS_NO_PATHCONV=1 docker compose run --rm -T -w /work/harness runner run_all.py
```

(`MSYS_NO_PATHCONV=1` is only needed in Git Bash on Windows; in PowerShell omit it.)

Output: `results/summary.md` plus raw JSON per method (`A_static.json`, `B_fixed.json`, `R_random.json`,
`P_change_aware.json`, `ground_truth.json`)
and per-run intermediate files under `results/work/`.

## Layout

- `app_v1/` – V1 Django app (orders). `orders/management/commands/drive.py` writes logical inputs
  through the API; `probe.py` is the rollback oracle run by V1.
- `harness/scenarios.py` – the seeded V2 changes (V1 + patches) and ground-truth labels.
- `harness/run_static.py` – Method A (django-migration-linter, Squawk).
- `harness/run_fixed.py` – Method B (fixed-data V1 → V2 → V1 cycle).
- `harness/run_random.py` – Method R (Hypothesis inputs from V2's model, 20 inputs x 10 seeds; generator in
  `app_v1/orders/management/commands/gen_random.py`).
- `harness/run_change_aware.py` – Method P (proposed): digest manifest of V1/V2 (models, services, views,
  migrations, per-field contract from `describe_contract.py`), change classification, targeted inputs,
  same V1 → V2 → V1 cycle. `P_TRACK_CODE=0` runs the ablation that ignores service/view code changes.
- `harness/validate_truth.py` – witness input per scenario to confirm the labels.
- `harness/report.py` – combines results, computes C = A + B, adds R and P.
- `build/` – generated V2 apps (recreated on each run).

Note: Python runs inside Docker because Windows Smart App Control blocks the psycopg binary DLL on the host.
