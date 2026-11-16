from django.core.validators import RegexValidator
from django.db import models

STATUS_CHOICES = [
    ("pending", "Beklemede"),
    ("paid", "Odendi"),
    ("shipped", "Kargoda"),
    ("cancelled", "Iptal"),
]

# V1 contract: Turkish mobile number in national format, e.g. 05321234567
phone_validator = RegexValidator(r"^05\d{9}$", "Telefon 05XXXXXXXXX formatinda olmali")


class Order(models.Model):
    customer_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, validators=[phone_validator])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    shipping_address = models.CharField(max_length=200)
    coupon_code = models.CharField(max_length=10, blank=True, default="")
    total_amount = models.IntegerField(help_text="Toplam tutar, TL (tam sayi)")
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
