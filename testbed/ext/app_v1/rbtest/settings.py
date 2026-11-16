import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "testbed-only"
DEBUG = False
ALLOWED_HOSTS = ["*"]
APP_VERSION = os.environ.get("RB_APP_VERSION", "v1")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django_migration_linter",
    "orders",
]
MIDDLEWARE = []
ROOT_URLCONF = "rbtest.urls"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("RB_DB", "rbtest"),
        "USER": "rbtest",
        "PASSWORD": "rbtest",
        "HOST": os.environ.get("RB_DB_HOST", "localhost"),
        "PORT": os.environ.get("RB_DB_PORT", "5433"),
    }
}
USE_TZ = True
TIME_ZONE = "Europe/Istanbul"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
MIGRATION_LINTER_OPTIONS = {"no_cache": True}
