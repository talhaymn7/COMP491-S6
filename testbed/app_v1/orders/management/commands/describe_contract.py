"""Method P, step 1: describe the data contract of *this* application version.

For every concrete field of the Order model, write a normalized descriptor
(type, nullability, length, choices, validators, defaults). The harness hashes
these descriptors and the data-defining source files into a digest manifest and
compares the manifests of V1 and V2.
"""
import json

from django.core.management.base import BaseCommand
from django.core.validators import RegexValidator
from django.db.models import NOT_PROVIDED

from orders.models import Order


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
        fields = {f.name: describe(f) for f in Order._meta.concrete_fields}
        with open(opts["out"], "w", encoding="utf-8") as f:
            json.dump({"model": "orders.Order", "fields": fields}, f, ensure_ascii=False, indent=1, sort_keys=True)
