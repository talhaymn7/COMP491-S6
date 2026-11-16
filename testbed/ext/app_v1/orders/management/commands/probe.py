"""Rollback oracle for the extended testbed, executed by the OLD version (V1).

For every resource and every stored record it checks that V1 can (1) list it, (2) read
it, (3) show the same logical values that were given as input, and (4) edit and save it.
It also checks that V1 can still create a new record of every resource and compute the
report. Each problem is recorded as a finding; the run never stops at the first problem.
"""
import json

from django.core.management.base import BaseCommand
from django.db import connection
from django.test import Client

TABLES = {"order": "orders_order", "customer": "orders_customer",
          "product": "orders_product", "shipment": "orders_shipment"}

CANONICAL_V1_INPUT = {
    "order": {"customer_name": "Probe Musteri", "phone": "05320000000", "status": "pending",
              "shipping_address": "Kayseri Merkez", "coupon_code": "", "total_tl": 10},
    "customer": {"full_name": "Probe Musteri", "email": "probe@example.com", "tier": "bronze",
                 "city": "Kayseri", "birth_year": 1990, "marketing_opt_in": False},
    "product": {"sku": "PRB-0001", "name": "Probe Urun", "category": "home", "price_tl": 10,
                "stock": 1, "unit": "pcs"},
    "shipment": {"carrier": "mng", "tracking_code": "PRB0000001", "status": "created",
                 "weight_grams": 100, "delivery_window": "morning", "address": "Kayseri Merkez"},
}


def _call(client, method, url, payload=None):
    try:
        if payload is None:
            resp = getattr(client, method)(url)
        else:
            resp = getattr(client, method)(url, json.dumps(payload), content_type="application/json")
        body = None
        try:
            body = resp.json()
        except Exception:
            pass
        return resp.status_code, body, None
    except Exception as exc:  # 500 raised by the test client
        return 500, None, f"{type(exc).__name__}: {str(exc).splitlines()[0][:200]}"


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--expect", required=True, help="JSON list of {id, input}")
        parser.add_argument("--out", required=True)

    def handle(self, *args, **opts):
        with open(opts["expect"], encoding="utf-8") as f:
            expected = {(e["input"].get("_resource", "order"), e["id"]): e["input"]
                        for e in json.load(f) if e.get("id")}
        client = Client(raise_request_exception=True)
        findings = []
        checked = 0

        def finding(step, error, resource, order_id=None, field=None):
            findings.append({"step": step, "resource": resource, "order_id": order_id,
                             "field": field, "error": error})

        for res, table in TABLES.items():
            code, _, err = _call(client, "get", f"/api/{res}/")
            if code != 200:
                finding("list", err or f"HTTP {code}", res)

            with connection.cursor() as cur:
                cur.execute(f"SELECT id FROM {table} ORDER BY id")
                ids = [r[0] for r in cur.fetchall()]

            for oid in ids:
                checked += 1
                code, body, err = _call(client, "get", f"/api/{res}/{oid}/")
                if code != 200:
                    finding("read", err or f"HTTP {code}", res, oid)
                    continue
                exp = expected.get((res, oid))
                if exp:
                    for field, want in exp.items():
                        if field.startswith("_") or field not in body:
                            continue
                        if body[field] != want:
                            finding("value", f"V1 shows {body[field]!r}, logical value is {want!r}", res, oid, field)
                code, body, err = _call(client, "patch", f"/api/{res}/{oid}/", {"note": "rollback-probe"})
                if code != 200:
                    detail = err or f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}"
                    finding("edit", detail, res, oid)

            code, body, err = _call(client, "post", f"/api/{res}/", CANONICAL_V1_INPUT[res])
            if code != 201:
                finding("create", err or f"HTTP {code} {body}", res)

        code, body, err = _call(client, "get", "/api/report/")
        if code != 200:
            finding("report", err or f"HTTP {code}", None)

        with open(opts["out"], "w", encoding="utf-8") as f:
            json.dump({"orders_checked": checked, "findings": findings}, f, ensure_ascii=False, indent=1)
