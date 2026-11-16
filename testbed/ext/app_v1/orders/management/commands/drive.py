"""Send logical inputs to *this* application version through its HTTP API.

Input file: JSON list of logical records; the key "_resource" selects the resource
(order, customer, product, shipment). Same request format for every version.
Output: JSON list of {"input": ..., "status": http_status, "id": created id or null}.
"""
import json

from django.core.management.base import BaseCommand
from django.test import Client


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--inputs", required=True)
        parser.add_argument("--out", required=True)

    def handle(self, *args, **opts):
        with open(opts["inputs"], encoding="utf-8") as f:
            inputs = json.load(f)
        client = Client(raise_request_exception=False)
        results = []
        for item in inputs:
            resource = item.get("_resource", "order")
            data = {k: v for k, v in item.items() if not k.startswith("_")}
            resp = client.post(f"/api/{resource}/", json.dumps(data), content_type="application/json")
            body = {}
            try:
                body = resp.json()
            except Exception:
                pass
            results.append({"input": item, "status": resp.status_code, "id": body.get("id"), "body": body})
        with open(opts["out"], "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)
