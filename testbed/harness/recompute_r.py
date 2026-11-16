"""Recompute R's 'first detecting input' from the stored probe outputs (no re-run)."""
import json
import statistics

from common import RESULTS, save
from run_random import first_detecting_input

rows = json.loads((RESULTS / "R_random.json").read_text(encoding="utf-8"))
for row in rows:
    for run in row["runs"]:
        work = RESULTS / "work" / f"R{run['seed']}" / row["scenario"]
        probe = json.loads((work / "probe.json").read_text(encoding="utf-8"))
        written = json.loads((work / "out_v2.json").read_text(encoding="utf-8"))
        run["first_detecting_input"] = first_detecting_input(probe, written)
    firsts = [r["first_detecting_input"] for r in row["runs"] if r["detected"]]
    row["mean_first_detecting_input"] = round(statistics.mean(firsts), 1) if firsts else None
    print(f"{row['scenario']:<24} first_inputs={firsts} mean={row['mean_first_detecting_input']}")
save("R_random.json", rows)
