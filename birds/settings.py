from dotenv import load_dotenv
from django.core.management.utils import get_random_secret_key
from pathlib import Path
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Ensures env variables are defined
missingEnv = False
varsMissing = []

if "DEBUG" not in os.environ:
    missingEnv = True
    varsMissing.append("DEBUG")

if "USE_SQLITE" not in os.environ:
    missingEnv = True
    varsMissing.append("USE_SQLITE")

if missingEnv:
    raise EnvironmentError(f"Your .env file is missing some definitions: {varsMissing}")

DEBUG = os.getenv("DEBUG") == "True"
USE_SQLITE = os.getenv("USE_SQLITE")

if USE_SQLITE == "True":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        }
    }

else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "test_db"),
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "widget_tweaks",
    "fullurl",
    "birds",
]

SECRET_KEY = os.getenv("django_secret_key", get_random_secret_key())

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

DEBUG = os.getenv("DEBUG") == "True"
STATIC_ROOT = os.path.join(BASE_DIR, "birds/collected_static")
STATIC_URL = os.path.join(BASE_DIR, "birds/static/")
ROOT_URLCONF = "birds.project_urls"
