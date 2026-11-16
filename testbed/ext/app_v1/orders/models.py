"""Extended testbed: four resources (order, customer, product, shipment), about 30 fields."""
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

# --- Order (same as the base testbed) -------------------------------------------------
STATUS_CHOICES = [
    ("pending", "Beklemede"),
    ("paid", "Odendi"),
    ("shipped", "Kargoda"),
    ("cancelled", "Iptal"),
]
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


# --- Customer ---------------------------------------------------------------------------
TIER_CHOICES = [("bronze", "Bronz"), ("silver", "Gumus"), ("gold", "Altin")]
email_validator = RegexValidator(r"^[a-z0-9.]+@[a-z0-9]+\.(com|net|org|tr)$", "Gecersiz e-posta")


class Customer(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.CharField(max_length=120, validators=[email_validator])
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default="bronze")
    city = models.CharField(max_length=50)
    birth_year = models.IntegerField(validators=[MinValueValidator(1900), MaxValueValidator(2010)])
    marketing_opt_in = models.BooleanField(default=False)
    note = models.TextField(blank=True, default="")


# --- Product ----------------------------------------------------------------------------
CATEGORY_CHOICES = [("electronics", "Elektronik"), ("books", "Kitap"), ("home", "Ev"), ("toys", "Oyuncak")]
UNIT_CHOICES = [("pcs", "Adet"), ("kg", "Kilogram")]
sku_validator = RegexValidator(r"^[A-Z]{3}-\d{4}$", "SKU AAA-0000 formatinda olmali")


class Product(models.Model):
    sku = models.CharField(max_length=12, validators=[sku_validator])
    name = models.CharField(max_length=80)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    price_tl = models.IntegerField(validators=[MinValueValidator(0)])
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=5, choices=UNIT_CHOICES, default="pcs")
    note = models.TextField(blank=True, default="")


# --- Shipment ---------------------------------------------------------------------------
CARRIER_CHOICES = [("yurtici", "Yurtici Kargo"), ("aras", "Aras Kargo"), ("mng", "MNG Kargo")]
SHIPMENT_STATUS = [("created", "Olusturuldu"), ("in_transit", "Yolda"),
                   ("delivered", "Teslim edildi"), ("returned", "Iade")]
WINDOW_CHOICES = [("morning", "Sabah"), ("afternoon", "Ogleden sonra"), ("evening", "Aksam")]
tracking_validator = RegexValidator(r"^[A-Z0-9]{10}$", "Takip kodu 10 karakter olmali")


class Shipment(models.Model):
    carrier = models.CharField(max_length=20, choices=CARRIER_CHOICES)
    tracking_code = models.CharField(max_length=20, validators=[tracking_validator])
    status = models.CharField(max_length=20, choices=SHIPMENT_STATUS, default="created")
    weight_grams = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(30000)])
    delivery_window = models.CharField(max_length=10, choices=WINDOW_CHOICES, default="afternoon")
    address = models.CharField(max_length=200)
    note = models.TextField(blank=True, default="")
