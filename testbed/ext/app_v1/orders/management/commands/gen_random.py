"""Method R input generator for the extended testbed: random, schema-based, NOT change-aware.

Runs inside the version under test (V2). For every input it picks one of the resources
and draws values for that resource's model fields (choices, null, max_length, regex
validators, min/max validators, booleans). It has no knowledge of what changed.
"""
import json

from django.core.management.base import BaseCommand
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from hypothesis import Phase, given, seed, settings
from hypothesis import strategies as st

from orders.services import RESOURCES

SKIP = {"id", "created_at", "note", "customer_note"}  # not part of the create API
INPUT_NAME = {("order", "total_amount"): "total_tl"}  # API name differs from column name
TEXT = st.characters(blacklist_categories=("Cs", "Cc"))


def strategy_for(field):
    if field.choices:
        s = st.sampled_from([c[0] for c in field.choices])
    elif isinstance(field, models.BooleanField):
        s = st.booleans()
    elif isinstance(field, models.IntegerField):
        lo = max([v.limit_value for v in field.validators if isinstance(v, MinValueValidator)], default=0)
        hi = min([v.limit_value for v in field.validators if isinstance(v, MaxValueValidator)], default=100_000)
        s = st.integers(min_value=lo, max_value=hi)
    else:
        regex = next((v.regex.pattern for v in field.validators if isinstance(v, RegexValidator)), None)
        if regex:
            s = st.from_regex(regex, fullmatch=True)
        else:
            s = st.text(TEXT, min_size=0 if field.blank else 1, max_size=field.max_length or 50)
    return st.one_of(st.none(), s) if field.null else s


def resource_strategy(name, model):
    fields = {INPUT_NAME.get((name, f.name), f.name): strategy_for(f)
              for f in model._meta.concrete_fields if f.name not in SKIP}
    return st.fixed_dictionaries(fields).map(lambda d, n=name: {"_resource": n, **d})


def input_strategy():
    return st.one_of([resource_strategy(name, model) for name, (model, _, _) in RESOURCES.items()])


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--n", type=int, required=True)
        parser.add_argument("--seed", type=int, required=True)
        parser.add_argument("--out", required=True)

    def handle(self, *args, **opts):
        drawn = []

        @seed(opts["seed"])
        @settings(max_examples=opts["n"], database=None, phases=[Phase.generate], deadline=None)
        @given(input_strategy())
        def draw(item):
            drawn.append(item)

        draw()
        drawn[:] = drawn[: opts["n"]]
        with open(opts["out"], "w", encoding="utf-8") as f:
            json.dump(drawn, f, ensure_ascii=False, indent=1)
