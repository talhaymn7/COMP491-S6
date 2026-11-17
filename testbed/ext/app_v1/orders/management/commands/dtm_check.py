"""Method B' : django-test-migrations used as the tool is designed to be used.

The tool tests *migrations* with historical models: data is created at the old
migration state, the new migration is applied, more data is created at the new
state, and then the migration is reversed (schema rollback). Application code
(services, views) is never executed. The same fixed data as method B is used.

Assertions a developer would typically write after the reverse migration:
  * the reverse migration succeeds,
  * every row can be read with the V1 historical model,
  * every row passes V1 model validation (full_clean),
  * the V1 fields of every row still hold the values that were written.
Runs inside the V2 application (it needs the V2 migration files).
"""
import json

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django_test_migrations.migrator import Migrator

APP = "orders"
MODEL = {"order": "Order", "customer": "Customer", "product": "Product", "shipment": "Shipment"}
FIELD = {"total_tl": "total_amount"}  # logical input name -> model field


def model_data(model, item):
    names = {f.name for f in model._meta.concrete_fields}
    return {FIELD.get(k, k): v for k, v in item.items()
            if not k.startswith("_") and FIELD.get(k, k) in names}


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--inputs", required=True)
        parser.add_argument("--inputs-v2", help="data written at the V2 state (default: --inputs)")
        parser.add_argument("--v1", required=True, help="last V1 migration name")
        parser.add_argument("--v2", required=True, help="last V2 migration name")
        parser.add_argument("--out", required=True)

    def handle(self, *args, **opts):
        with open(opts["inputs"], encoding="utf-8") as f:
            inputs = json.load(f)
        inputs_v2 = inputs
        if opts.get("inputs_v2"):
            with open(opts["inputs_v2"], encoding="utf-8") as f:
                inputs_v2 = json.load(f)
        findings, written = [], []

        def finding(step, error, resource=None, row=None, field=None):
            findings.append({"step": step, "resource": resource, "order_id": row, "field": field,
                             "error": str(error)[:200]})

        migrator = Migrator(database="default")
        try:
            # 1. old state: write the fixed data with the V1 historical models
            state = migrator.apply_initial_migration((APP, opts["v1"]))
            for item in inputs:
                res = item.get("_resource", "order")
                model = state.apps.get_model(APP, MODEL[res])
                obj = model.objects.create(**model_data(model, item))
                written.append((res, obj.pk, item))
            # 2. new state: apply the tested migration, write the fixed data again
            try:
                state = migrator.apply_tested_migration((APP, opts["v2"]))
            except Exception as exc:
                finding("forward_migration", f"{type(exc).__name__}: {exc}")
                raise
            for item in inputs_v2:
                res = item.get("_resource", "order")
                model = state.apps.get_model(APP, MODEL[res])
                try:
                    obj = model.objects.create(**model_data(model, item))
                    written.append((res, obj.pk, item))
                except Exception as exc:
                    finding("write_v2", f"{type(exc).__name__}: {exc}", res)
            # 3. rollback: reverse the migration and check the data with the V1 models
            try:
                state = migrator.apply_tested_migration((APP, opts["v1"]))
            except Exception as exc:
                finding("reverse_migration", f"{type(exc).__name__}: {exc}")
                raise
            for res, pk, item in written:
                model = state.apps.get_model(APP, MODEL[res])
                try:
                    obj = model.objects.get(pk=pk)
                except Exception as exc:
                    finding("read", f"{type(exc).__name__}: {exc}", res, pk)
                    continue
                try:
                    obj.full_clean()
                except ValidationError as exc:
                    finding("validation", exc.message_dict, res, pk)
                for field, want in model_data(model, item).items():
                    got = getattr(obj, field)
                    if got != want:
                        finding("value", f"{got!r} != {want!r}", res, pk, field)
        except Exception as exc:
            if not findings:
                finding("error", f"{type(exc).__name__}: {exc}")
        finally:
            try:
                migrator.reset()
            except Exception:
                pass
        with open(opts["out"], "w", encoding="utf-8") as f:
            json.dump({"rows": len(written), "findings": findings}, f, ensure_ascii=False, indent=1, default=str)
