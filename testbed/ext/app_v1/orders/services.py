"""Business logic of the extended application. This is the code that is rolled back."""
from django.core.exceptions import ValidationError
from django.db.models import Sum

from .models import (CARRIER_CHOICES, CATEGORY_CHOICES, SHIPMENT_STATUS, STATUS_CHOICES, TIER_CHOICES,
                     UNIT_CHOICES, WINDOW_CHOICES, Customer, Order, Product, Shipment)

STATUS_LABELS = dict(STATUS_CHOICES)
TIER_LABELS = dict(TIER_CHOICES)
CATEGORY_LABELS = dict(CATEGORY_CHOICES)
UNIT_LABELS = dict(UNIT_CHOICES)
CARRIER_LABELS = dict(CARRIER_CHOICES)
SHIPMENT_STATUS_LABELS = dict(SHIPMENT_STATUS)
WINDOW_LABELS = dict(WINDOW_CHOICES)
CURRENT_YEAR = 2026


# --- Order ------------------------------------------------------------------------------
def order_rules(order):
    """Business rule kept in code, not in the model."""
    if order.coupon_code and order.total_amount < 100:
        raise ValidationError({"coupon_code": ["Kupon yalnizca 100 TL ve uzeri siparislerde kullanilabilir"]})


def create_order(data):
    order = Order(
        customer_name=data["customer_name"],
        phone=data["phone"],
        status=data.get("status", "pending"),
        shipping_address=data["shipping_address"],
        coupon_code=data.get("coupon_code", ""),
        total_amount=int(data["total_tl"]),
    )
    order.full_clean()
    order_rules(order)
    order.save()
    return order


def order_summary(order):
    return {
        "id": order.id,
        "customer_name": order.customer_name,
        "phone": order.phone,
        "status": order.status,
        "status_label": STATUS_LABELS[order.status],
        "shipping_address": order.shipping_address,
        "shipping_label": order.shipping_address.upper(),
        "coupon_code": order.coupon_code,
        "total_tl": order.total_amount,
        "note": order.note,
    }


# --- Customer ---------------------------------------------------------------------------
def create_customer(data):
    customer = Customer(
        full_name=data["full_name"],
        email=data["email"],
        tier=data.get("tier", "bronze"),
        city=data["city"],
        birth_year=int(data["birth_year"]),
        marketing_opt_in=bool(data.get("marketing_opt_in", False)),
    )
    customer.full_clean()
    customer.save()
    return customer


def customer_summary(customer):
    return {
        "id": customer.id,
        "full_name": customer.full_name,
        "email": customer.email,
        "email_domain": customer.email.split("@")[1],
        "tier": customer.tier,
        "tier_label": TIER_LABELS[customer.tier],
        "city": customer.city,
        "city_label": customer.city.upper(),
        "birth_year": customer.birth_year,
        "age": CURRENT_YEAR - customer.birth_year,
        "marketing_opt_in": customer.marketing_opt_in,
        "note": customer.note,
    }


# --- Product ----------------------------------------------------------------------------
def create_product(data):
    product = Product(
        sku=data["sku"],
        name=data["name"],
        category=data["category"],
        price_tl=int(data["price_tl"]),
        stock=int(data.get("stock", 0)),
        unit=data.get("unit", "pcs"),
    )
    product.full_clean()
    product.save()
    return product


def product_summary(product):
    return {
        "id": product.id,
        "sku": product.sku,
        "sku_prefix": product.sku[:3],
        "name": product.name,
        "category": product.category,
        "category_label": CATEGORY_LABELS[product.category],
        "price_tl": product.price_tl,
        "stock": product.stock,
        "unit": product.unit,
        "unit_label": UNIT_LABELS[product.unit],
        "note": product.note,
    }


# --- Shipment ---------------------------------------------------------------------------
def create_shipment(data):
    shipment = Shipment(
        carrier=data["carrier"],
        tracking_code=data["tracking_code"],
        status=data.get("status", "created"),
        weight_grams=int(data["weight_grams"]),
        delivery_window=data.get("delivery_window", "afternoon"),
        address=data["address"],
    )
    shipment.full_clean()
    shipment.save()
    return shipment


def shipment_summary(shipment):
    return {
        "id": shipment.id,
        "carrier": shipment.carrier,
        "carrier_label": CARRIER_LABELS[shipment.carrier],
        "tracking_code": shipment.tracking_code,
        "tracking_suffix": shipment.tracking_code[-4:],
        "status": shipment.status,
        "status_label": SHIPMENT_STATUS_LABELS[shipment.status],
        "weight_grams": shipment.weight_grams,
        "delivery_window": shipment.delivery_window,
        "window_label": WINDOW_LABELS[shipment.delivery_window],
        "address": shipment.address,
        "note": shipment.note,
    }


# --- Shared -----------------------------------------------------------------------------
RESOURCES = {
    "order": (Order, create_order, order_summary),
    "customer": (Customer, create_customer, customer_summary),
    "product": (Product, create_product, product_summary),
    "shipment": (Shipment, create_shipment, shipment_summary),
}


def update_note(resource, obj, note):
    obj.note = note
    obj.full_clean()
    if resource == "order":
        order_rules(obj)
    obj.save()
    return obj


def report():
    revenue = Order.objects.exclude(status="cancelled").aggregate(s=Sum("total_amount"))["s"] or 0
    stock_value = sum(p.price_tl * p.stock for p in Product.objects.all())
    by_carrier = {code: 0 for code in CARRIER_LABELS}
    for s in Shipment.objects.all():
        by_carrier[s.carrier] += 1
    opted_in = Customer.objects.filter(marketing_opt_in=True).count()
    return {"revenue_tl": revenue, "stock_value_tl": stock_value,
            "shipments_by_carrier": by_carrier, "customers_opted_in": opted_in}
