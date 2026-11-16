"""Extended testbed: new seeded V2 changes on a four-resource application.

These scenarios were written after the rules of method P were frozen (first commit of this repository)
and before P was run on them. They add change types that were not part of the base
testbed (numeric range validators, a business rule kept in code, a release with several
changes, a value semantics change on another resource) and four safe control changes.
"""

DESCRIPTION = ("Extended testbed: Django 5.2 app with 4 resources (order, customer, product, shipment), "
               "about 30 fields, PostgreSQL 16, 12 seeded V2 changes (8 rollback-incompatible, 4 safe controls).")

MODELS = "orders/models.py"
SERVICES = "orders/services.py"

FIXED_INPUTS = [
    {"_resource": "order", "customer_name": "Ayse Yilmaz", "phone": "05321112233", "status": "pending",
     "shipping_address": "Talas, Kayseri", "coupon_code": "", "total_tl": 250},
    {"_resource": "customer", "full_name": "Ayse Yilmaz", "email": "ayse.yilmaz@example.com", "tier": "silver",
     "city": "Kayseri", "birth_year": 1990, "marketing_opt_in": True},
    {"_resource": "product", "sku": "ELK-1001", "name": "Kablosuz Kulaklik", "category": "electronics",
     "price_tl": 1500, "stock": 25, "unit": "pcs"},
    {"_resource": "shipment", "carrier": "yurtici", "tracking_code": "YT12345678", "status": "in_transit",
     "weight_grams": 1200, "delivery_window": "morning", "address": "Talas, Kayseri"},
    {"_resource": "order", "customer_name": "Mehmet Demir", "phone": "05559998877", "status": "paid",
     "shipping_address": "Cankaya, Ankara", "coupon_code": "YAZ10", "total_tl": 1200},
    {"_resource": "customer", "full_name": "Mehmet Demir", "email": "mehmet@example.net", "tier": "bronze",
     "city": "Ankara", "birth_year": 1985, "marketing_opt_in": False},
    {"_resource": "product", "sku": "KTP-2002", "name": "Roman", "category": "books",
     "price_tl": 120, "stock": 100, "unit": "pcs"},
    {"_resource": "shipment", "carrier": "aras", "tracking_code": "AR98765432", "status": "created",
     "weight_grams": 500, "delivery_window": "evening", "address": "Cankaya, Ankara"},
]

ORDER, CUSTOMER, PRODUCT, SHIPMENT = (dict(FIXED_INPUTS[i]) for i in range(4))

SCENARIOS = [
    # ---------------------------------------------------------------- safe controls
    {
        "id": "X0_product_barcode",
        "title": "V2 adds an optional, nullable barcode to products",
        "category": "control", "rollback_incompatible": False,
        "patches": [
            (MODELS, '    unit = models.CharField(max_length=5, choices=UNIT_CHOICES, default="pcs")\n',
             '    unit = models.CharField(max_length=5, choices=UNIT_CHOICES, default="pcs")\n'
             '    barcode = models.CharField(max_length=13, null=True, blank=True)\n'),
            (SERVICES, '        unit=data.get("unit", "pcs"),\n',
             '        unit=data.get("unit", "pcs"),\n        barcode=data.get("barcode"),\n'),
        ],
    },
    {
        "id": "X1_product_name_shorter",
        "title": "V2 limits product names to 60 characters (narrowing)",
        "category": "control", "rollback_incompatible": False,
        "patches": [(MODELS, "name = models.CharField(max_length=80)", "name = models.CharField(max_length=60)")],
    },
    {
        "id": "X2_order_gift_wrap",
        "title": "V2 adds gift_wrap boolean with a database default",
        "category": "control", "rollback_incompatible": False,
        "patches": [
            (MODELS, '    total_amount = models.IntegerField(help_text="Toplam tutar, TL (tam sayi)")\n',
             '    total_amount = models.IntegerField(help_text="Toplam tutar, TL (tam sayi)")\n'
             '    gift_wrap = models.BooleanField(default=False, db_default=False)\n'),
            (SERVICES, '        total_amount=int(data["total_tl"]),\n',
             '        total_amount=int(data["total_tl"]),\n        gift_wrap=bool(data.get("gift_wrap", False)),\n'),
        ],
    },
    {
        "id": "X3_category_removed",
        "title": "V2 no longer offers the product category 'toys'",
        "category": "control", "rollback_incompatible": False,
        "patches": [(MODELS, '("home", "Ev"), ("toys", "Oyuncak")]', '("home", "Ev")]')],
    },
    # ------------------------------------------------------- rollback-incompatible
    {
        "id": "E1_birth_year_range",
        "title": "V2 accepts customers born up to 2015 (numeric range validator)",
        "category": "value_range", "rollback_incompatible": True,
        "patches": [(MODELS, "MaxValueValidator(2010)", "MaxValueValidator(2015)")],
    },
    {
        "id": "E2_new_carrier",
        "title": "V2 adds the carrier 'ptt'",
        "category": "value_range", "rollback_incompatible": True,
        "patches": [(MODELS, '("mng", "MNG Kargo")]', '("mng", "MNG Kargo"), ("ptt", "PTT Kargo")]')],
    },
    {
        "id": "E3_price_with_vat",
        "title": "V2 stores product prices including 20% VAT (no schema change)",
        "category": "semantic", "rollback_incompatible": True,
        "patches": [
            (SERVICES, '        price_tl=int(data["price_tl"]),\n',
             '        price_tl=round(int(data["price_tl"]) * 1.2),\n'),
            (SERVICES, '"price_tl": product.price_tl,', '"price_tl": round(product.price_tl / 1.2),'),
        ],
    },
    {
        "id": "E4_coupon_rule_relaxed",
        "title": "V2 allows coupons on orders below 100 TL (business rule in code)",
        "category": "business_rule", "rollback_incompatible": True,
        "patches": [(SERVICES, "if order.coupon_code and order.total_amount < 100:",
                     "if order.coupon_code and order.total_amount < 0:")],
    },
    {
        "id": "E5_release_category_city",
        "title": "V2 release with two changes: new category 'garden' and city up to 100 characters",
        "category": "multi_change", "rollback_incompatible": True,
        "patches": [
            (MODELS, '("toys", "Oyuncak")]', '("toys", "Oyuncak"), ("garden", "Bahce")]'),
            (MODELS, "city = models.CharField(max_length=50)", "city = models.CharField(max_length=100)"),
        ],
    },
    {
        "id": "E6_sku_longer_digits",
        "title": "V2 accepts SKUs with 4 to 6 digits",
        "category": "format_requirement", "rollback_incompatible": True,
        "patches": [(MODELS, 'RegexValidator(r"^[A-Z]{3}-\\d{4}$"', 'RegexValidator(r"^[A-Z]{3}-\\d{4,6}$"')],
    },
    {
        "id": "E7_tracking_nullable",
        "title": "V2 creates shipments before a tracking code exists (NULL)",
        "category": "null_absent", "rollback_incompatible": True,
        "patches": [
            (MODELS, "tracking_code = models.CharField(max_length=20, validators=[tracking_validator])",
             "tracking_code = models.CharField(max_length=20, validators=[tracking_validator], null=True, blank=True)"),
            (SERVICES, '        tracking_code=data["tracking_code"],', '        tracking_code=data.get("tracking_code"),'),
            (SERVICES, '"tracking_suffix": shipment.tracking_code[-4:],',
             '"tracking_suffix": (shipment.tracking_code or "")[-4:],'),
        ],
    },
    {
        "id": "E8_split_full_name",
        "title": "V2 splits full_name into first_name and last_name",
        "category": "schema_structure", "rollback_incompatible": True,
        "patches": [
            (MODELS, "    full_name = models.CharField(max_length=100)\n",
             '    first_name = models.CharField(max_length=50, default="")\n'
             '    last_name = models.CharField(max_length=50, default="")\n'),
            (SERVICES, '        full_name=data["full_name"],',
             '        first_name=(data.get("full_name") or "").split(" ")[0],\n'
             '        last_name=" ".join((data.get("full_name") or "").split(" ")[1:]),'),
            (SERVICES, '"full_name": customer.full_name,',
             '"full_name": f"{customer.first_name} {customer.last_name}".strip(),'),
        ],
    },
]

WITNESS = {
    "X0_product_barcode": {**PRODUCT, "barcode": "8690000000001"},
    "X1_product_name_shorter": PRODUCT,
    "X2_order_gift_wrap": {**ORDER, "gift_wrap": True},
    "X3_category_removed": PRODUCT,
    "E1_birth_year_range": {**CUSTOMER, "birth_year": 2013},
    "E2_new_carrier": {**SHIPMENT, "carrier": "ptt"},
    "E3_price_with_vat": PRODUCT,
    "E4_coupon_rule_relaxed": {**ORDER, "coupon_code": "YAZ10", "total_tl": 50},
    "E5_release_category_city": {**PRODUCT, "category": "garden"},
    "E6_sku_longer_digits": {**PRODUCT, "sku": "ELK-10012"},
    "E7_tracking_nullable": {**SHIPMENT, "tracking_code": None},
    "E8_split_full_name": CUSTOMER,
}
