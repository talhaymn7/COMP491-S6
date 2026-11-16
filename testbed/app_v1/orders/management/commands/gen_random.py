"""Method R input generator: random, schema-based, NOT change-aware.

Runs inside the version under test (V2) and derives Hypothesis strategies from that
version's Order model only (choices, null, max_length, RegexValidator, blank).
It has no knowledge of what changed between V1 and V2.
"""
import json

from django.core.management.base import BaseCommand
from django.core.validators import RegexValidator
from django.db import models
from hypothesis import Phase, given, seed, settings
from hypothesis import strategies as st

from orders.models import Order

SKIP = {"id", "created_at", "note", "customer_note"}  # not part of the create API
INPUT_NAME = {"total_amount": "total_tl"}             # API name differs from column name
TEXT = st.characters(blacklist_categories=("Cs", "Cc"))


def strategy_for(field):
    if field.choices:
        s = st.sampled_from([c[0] for c in field.choices])
    elif isinstance(field, models.IntegerField):
        s = st.integers(min_value=0, max_value=100_000)
    else:
        regex = next((v.regex.pattern for v in field.validators if isinstance(v, RegexValidator)), None)
        if regex:
            s = st.from_regex(regex, fullmatch=True)
        else:
            s = st.text(TEXT, min_size=0 if field.blank else 1, max_size=field.max_length or 50)
    return st.one_of(st.none(), s) if field.null else s


def input_strategy():
    fields = {INPUT_NAME.get(f.name, f.name): strategy_for(f)
              for f in Order._meta.concrete_fields if f.name not in SKIP}
    return st.fixed_dictionaries(fields)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--n", type=int, required=True)
        parser.add_argument("--seed", type=int, required=True)
        parser.add_argument("--out", required=True)

    def handle(self, *args, **opts):
        drawn = []

        # One Hypothesis example per input, exactly as a normal @given test would see them.
        @seed(opts["seed"])
        @settings(max_examples=opts["n"], database=None, phases=[Phase.generate], deadline=None)
        @given(input_strategy())
        def draw(item):
            drawn.append(item)

        draw()
        drawn[:] = drawn[: opts["n"]]
        with open(opts["out"], "w", encoding="utf-8") as f:
            json.dump(drawn, f, ensure_ascii=False, indent=1)
