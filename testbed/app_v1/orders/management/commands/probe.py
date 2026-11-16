"""Rollback oracle, executed by the OLD version (V1) against the shared database.

For every stored order it checks that V1 can (1) list it, (2) read it, (3) show the
same business values that were given as logical input, and (4) edit and save it.
It also checks that V1 can still create new orders and compute the revenue report.
Each problem is recorded as a finding; the run never stops at the first problem.
"""
import json

from django.core.management.base import BaseCommand
from django.db import connection
from django.test import Client

CANONICAL_V1_INPUT = {
    "customer_name": "Probe Musteri",
    "phone": "05320000000",
    "status": "pending",
    "shipping_address": "Kayseri Merkez",
    "coupon_code": "",
    "total_tl": 10,
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
            expected = {e["id"]: e["input"] for e in json.load(f) if e.get("id")}
        client = Client(raise_request_exception=True)
        findings = []

        def finding(step, error, order_id=None, field=None):
            findings.append({"step": step, "order_id": order_id, "field": field, "error": error})

        code, _, err = _call(client, "get", "/orders/")
        if code != 200:
            finding("list", err or f"HTTP {code}")

        with connection.cursor() as cur:
            cur.execute("SELECT id FROM orders_order ORDER BY id")
            ids = [r[0] for r in cur.fetchall()]

        for oid in ids:
            code, body, err = _call(client, "get", f"/orders/{oid}/")
            if code != 200:
                finding("read", err or f"HTTP {code}", oid)
                continue
            exp = expected.get(oid)
            if exp:
                checks = {
                    "customer_name": (body["customer_name"], exp["customer_name"]),
                    "phone": (body["phone"], exp["phone"]),
                    "status": (body["status"], exp.get("status", "pending")),
                    "total_tl": (body["total_tl"], exp["total_tl"]),
                    "coupon_code": (body["coupon_code"], exp.get("coupon_code", "")),
                    "shipping_address": (body["shipping_label"], (exp.get("shipping_address") or "").upper()),
                }
                for field, (got, want) in checks.items():
                    if got != want:
                        finding("value", f"V1 shows {got!r}, logical value is {want!r}", oid, field)
            code, body, err = _call(client, "patch", f"/orders/{oid}/", {"note": "rollback-probe"})
            if code != 200:
                detail = err or f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}"
                finding("edit", detail, oid)

        code, body, err = _call(client, "post", "/orders/", CANONICAL_V1_INPUT)
        if code != 201:
            finding("create", err or f"HTTP {code} {body}")

        code, body, err = _call(client, "get", "/report/")
        if code != 200:
            finding("report", err or f"HTTP {code}")

        with open(opts["out"], "w", encoding="utf-8") as f:
            json.dump({"orders_checked": len(ids), "findings": findings}, f, ensure_ascii=False, indent=1)
