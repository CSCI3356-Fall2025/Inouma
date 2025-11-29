import logging
from pathlib import Path
import os

try:
    import pyrebase
except Exception:
    pyrebase = None

from decouple import config as env_config


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Load secret key from .env
SECRET_KEY = env_config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]


INSTALLED_APPS = [
    # Django default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',

    # Accounts
    'accounts',

    # Machines
    'machines',

    # Locations
    'locations',

    # Scheduling
    'scheduling',

    # Team Members App
    'team',
  
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Inouma.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        'DIRS': [BASE_DIR / 'templates'],

        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Inouma.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
# Add these lines:
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


logger = logging.getLogger(__name__)

firebase = None
auth = None
if pyrebase is not None:
    try:
        # Use python-decouple to read .env values so they are respected in development
        firebase_config = {
            "apiKey": env_config("FIREBASE_API_KEY", default=""),
            "authDomain": env_config("FIREBASE_AUTH_DOMAIN", default=""),
            "databaseURL": env_config("FIREBASE_DATABASE_URL", default=""),
            "storageBucket": env_config("FIREBASE_STORAGE_BUCKET", default=""),
        }
        # Only initialize if at least one key is present
        if any(firebase_config.values()):
            firebase = pyrebase.initialize_app(firebase_config)
            auth = firebase.auth()
        else:
            # avoid duplicate prints from the autoreloader by only warning in main process
            if os.environ.get("RUN_MAIN") == "true" or os.environ.get("RUN_MAIN") is None:
                logger.warning(
                    "Firebase configuration not found in environment; skipping pyrebase initialization."
                )
    except Exception:
        logger.warning(
            "Failed to initialize pyrebase. Firebase features will be disabled.", exc_info=True)
else:
    if os.environ.get("RUN_MAIN") == "true" or os.environ.get("RUN_MAIN") is None:
        logger.warning(
            "pyrebase package not installed; Firebase features will be disabled.")


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}


AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'accounts.backends.model_backend.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',  # keep default for admin access
]

# Redirect URLS for login/logout
LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/home'
LOGOUT_REDIRECT_URL = '/'

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@inouma.local"

# Media files (user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# For development (prints to console):
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# For production with SMTP:
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # or your SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'schmidln@bc.edu' ## the email used to send emails
EMAIL_HOST_PASSWORD = 'ayvw kfhu tvrj ynqs' ## your app password
## set app password here: https://myaccount.google.com/apppasswords
DEFAULT_FROM_EMAIL = 'schmidln@bc.edu' ## the email displayed to recipients

