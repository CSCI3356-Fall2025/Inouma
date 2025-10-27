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

    # Local apps
    'accounts',
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
        'DIRS': [BASE_DIR / 'templates'],  # optional templates folder
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
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


firebase = None
auth = None
if pyrebase is not None:
    try:
        firebase_config = {
            "apiKey": os.getenv("FIREBASE_API_KEY"),
            "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
            "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
            "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
        }
        # Only initialize if at least one key is present
        if any(firebase_config.values()):
            firebase = pyrebase.initialize_app(firebase_config)
            auth = firebase.auth()
        else:
            # missing firebase credentials; keep auth as None
            print("Warning: Firebase configuration not found in environment; skipping pyrebase initialization.")
    except Exception:
        print("Warning: Failed to initialize pyrebase. Firebase features will be disabled.")
else:
    print("Warning: pyrebase package not installed; Firebase features will be disabled.")


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'accounts.firebase_auth.firebase_authentication.FirebaseAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}


AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'accounts.backends.model_backend.ModelBackend',
]
