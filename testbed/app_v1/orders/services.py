"""Business logic of the application. This is the code that is rolled back."""
from django.db.models import Sum

from .models import STATUS_CHOICES, Order

STATUS_LABELS = dict(STATUS_CHOICES)


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
    order.save()
    return order


def order_summary(order):
    return {
        "id": order.id,
        "customer_name": order.customer_name,
        "phone": order.phone,
        "status": order.status,
        "status_label": STATUS_LABELS[order.status],
        "shipping_label": order.shipping_address.upper(),
        "coupon_code": order.coupon_code,
        "total_tl": order.total_amount,
        "note": order.note,
    }


def update_note(order, note):
    order.note = note
    order.full_clean()
    order.save()
    return order


def revenue_report():
    agg = Order.objects.exclude(status="cancelled").aggregate(s=Sum("total_amount"))
    return {"revenue_tl": agg["s"] or 0}
