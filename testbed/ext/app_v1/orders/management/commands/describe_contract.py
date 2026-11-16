"""Method P, step 1 (extended testbed): describe the data contract of this version.

Same normalized field descriptor as in the base testbed, for every model of every
resource; keys are "<resource>.<field>".
"""
import json

from django.core.management.base import BaseCommand
from django.core.validators import RegexValidator
from django.db.models import NOT_PROVIDED

from orders.services import RESOURCES


def describe(field):
    return {
        "column": field.column,
        "type": type(field).__name__,
        "null": field.null,
        "blank": field.blank,
        "max_length": getattr(field, "max_length", None),
        "choices": sorted(c[0] for c in field.choices) if field.choices else None,
        "regex": sorted(v.regex.pattern for v in field.validators if isinstance(v, RegexValidator)),
        "python_default": field.default is not NOT_PROVIDED,
        "db_default": getattr(field, "db_default", NOT_PROVIDED) is not NOT_PROVIDED,
    }


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--out", required=True)

    def handle(self, *args, **opts):
        fields = {f"{name}.{f.name}": describe(f)
                  for name, (model, _, _) in RESOURCES.items() for f in model._meta.concrete_fields}
        with open(opts["out"], "w", encoding="utf-8") as f:
            json.dump({"model": "orders.*", "fields": fields}, f, ensure_ascii=False, indent=1, sort_keys=True)
