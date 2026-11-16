"""Seeded V2 changes (one change per scenario, mutation-analysis style).

Every scenario = V1 source + textual patches. `rollback_incompatible` is the ground
truth: does running V1 again on data written by V2 break V1 behaviour?
Categories follow the proposal: value_range, null_absent, format_requirement,
semantic (meaning of a value changes, no schema change) and schema_structure.
"""

MODELS = "orders/models.py"
SERVICES = "orders/services.py"

RENAME_MIGRATION = """from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("orders", "0001_initial")]
    operations = [migrations.RenameField("order", "note", "customer_note")]
"""

SCENARIOS = [
    {
        "id": "S0_safe_add_nullable",
        "title": "V2 adds an optional gift_message column (nullable)",
        "category": "control",
        "rollback_incompatible": False,
        "patches": [
            (MODELS, '    note = models.TextField(blank=True, default="")\n',
             '    note = models.TextField(blank=True, default="")\n'
             '    gift_message = models.TextField(null=True, blank=True)\n'),
            (SERVICES, '        total_amount=int(data["total_tl"]),\n',
             '        total_amount=int(data["total_tl"]),\n'
             '        gift_message=data.get("gift_message"),\n'),
        ],
    },
    {
        "id": "S1_enum_new_value",
        "title": "V2 adds new order status 'partially_shipped'",
        "category": "value_range",
        "rollback_incompatible": True,
        "patches": [
            (MODELS, '    ("shipped", "Kargoda"),\n',
             '    ("shipped", "Kargoda"),\n    ("partially_shipped", "Kismi kargo"),\n'),
        ],
    },
    {
        "id": "S2_nullable_address",
        "title": "V2 allows store pickup: shipping_address may be NULL",
        "category": "null_absent",
        "rollback_incompatible": True,
        "patches": [
            (MODELS, 'shipping_address = models.CharField(max_length=200)',
             'shipping_address = models.CharField(max_length=200, null=True, blank=True)'),
            (SERVICES, '        shipping_address=data["shipping_address"],',
             '        shipping_address=data.get("shipping_address"),'),
            (SERVICES, '"shipping_label": order.shipping_address.upper(),',
             '"shipping_label": (order.shipping_address or "").upper(),'),
        ],
    },
    {
        "id": "S3_phone_e164",
        "title": "V2 stores phone numbers in E.164 format (+905...)",
        "category": "format_requirement",
        "rollback_incompatible": True,
        "patches": [
            (MODELS, 'RegexValidator(r"^05\\d{9}$"', 'RegexValidator(r"^\\+905\\d{9}$"'),
            (SERVICES, '        phone=data["phone"],',
             '        phone="+9" + data["phone"] if data["phone"].startswith("05") else data["phone"],'),
            (SERVICES, '        "phone": order.phone,',
             '        "phone": order.phone[2:] if order.phone.startswith("+90") else order.phone,'),
        ],
    },
    {
        "id": "S4_amount_in_kurus",
        "title": "V2 stores total_amount in kurus instead of TL (no schema change)",
        "category": "semantic",
        "rollback_incompatible": True,
        "patches": [
            (SERVICES, 'total_amount=int(data["total_tl"]),', 'total_amount=int(data["total_tl"]) * 100,'),
            (SERVICES, '"total_tl": order.total_amount,', '"total_tl": order.total_amount // 100,'),
            (SERVICES, 'return {"revenue_tl": agg["s"] or 0}', 'return {"revenue_tl": (agg["s"] or 0) // 100}'),
        ],
    },
    {
        "id": "S5_coupon_longer",
        "title": "V2 allows coupon codes up to 32 characters",
        "category": "value_range",
        "rollback_incompatible": True,
        "patches": [
            (MODELS, 'coupon_code = models.CharField(max_length=10,', 'coupon_code = models.CharField(max_length=32,'),
        ],
    },
    {
        "id": "S6_currency_not_null",
        "title": "V2 adds NOT NULL currency column (default only in Python)",
        "category": "schema_structure",
        "rollback_incompatible": True,
        "patches": [
            (MODELS, '    note = models.TextField(blank=True, default="")\n',
             '    note = models.TextField(blank=True, default="")\n'
             '    currency = models.CharField(max_length=3, default="TRY")\n'),
            (SERVICES, '        total_amount=int(data["total_tl"]),\n',
             '        total_amount=int(data["total_tl"]),\n'
             '        currency=data.get("currency", "TRY"),\n'),
        ],
    },
    {
        "id": "S7_rename_note",
        "title": "V2 renames column note -> customer_note",
        "category": "schema_structure",
        "rollback_incompatible": True,
        "patches": [
            (MODELS, '    note = models.TextField(blank=True, default="")',
             '    customer_note = models.TextField(blank=True, default="")'),
            (SERVICES, '"note": order.note,', '"note": order.customer_note,'),
            (SERVICES, '    order.note = note\n', '    order.customer_note = note\n'),
        ],
        "files": {"orders/migrations/0002_rename_note.py": RENAME_MIGRATION},
    },
]
