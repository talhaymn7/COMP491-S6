"""Select the testbed: RB_SUITE=base (default, testbed/) or RB_SUITE=ext (testbed/ext/)."""
import os
from pathlib import Path

SUITE = os.environ.get("RB_SUITE", "base")
ROOT = Path(__file__).resolve().parent.parent

if SUITE == "ext":
    from ext_scenarios import DESCRIPTION, FIXED_INPUTS, SCENARIOS, WITNESS  # noqa: F401
    APP_ROOT = ROOT / "ext"
else:
    from scenarios import DESCRIPTION, FIXED_INPUTS, SCENARIOS, WITNESS  # noqa: F401
    APP_ROOT = ROOT
