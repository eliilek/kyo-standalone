import os
import dj_database_url
import django_heroku

def get_secret(key, default=None):
    value = os.getenv(key, default)
    if value and os.path.isfile(value):
        with open(value) as f:
            return f.read()
    return value

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    default="%ppjxiq8eyx=rj(0s(rzgziq&f@h0i!@gi1v1f2pw@yi4+an%0",
)
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Application definition

INSTALLED_APPS = [
    'daphne',
    'django_rq',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'kyoapp',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'cloudinary',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'kyoapp.middleware.AuthRequiredMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'debug': DEBUG,
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'

RQ_QUEUES = {
    'default': {
        'URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        'DEFAULT_TIMEOUT': 500,
    }
}

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

# set database, it can be set to SQLite or Postgres

DB_SQLITE = "sqlite"
DB_POSTGRESQL = "postgresql"

DATABASES_ALL = {
    DB_SQLITE: {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR + "/db.sqlite3",
    },
    DB_POSTGRESQL: {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "NAME": os.environ.get("POSTGRES_NAME", "postgres"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": get_secret("POSTGRES_PASSWORD", "postgres"),
        "PORT": int(os.environ.get("POSTGRES_PORT", "5432")),
    },
}

DATABASES = {"default": DATABASES_ALL[os.environ.get("DJANGO_DB", DB_SQLITE)]}

#if IS_HEROKU_APP:
#    DATABASES = {
#        'default': dj_database_url.config(
#            env="DATABASE_URL",
#            conn_max_age=600,
#            conn_health_checks=True,
#            ssl_require=True,
#            )
#    }
#else:
#    DATABASES = {
#        "default": {
#            "ENGINE": "django.db.backends.sqlite3",
#            "NAME": BASE_DIR + "/db.sqlite3",
#        }
#   }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Chicago'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'staticfiles')
STATIC_URL = '/static/'

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = [
    os.path.join(PROJECT_ROOT, 'static'),
]

# Activate Django-Heroku.
django_heroku.settings(locals())

LOGIN_URL = '/accounts'
LOGIN_REDIRECT_URL = '/'

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
#TODO Edit below
#AWS_STORAGE_BUCKET_NAME = 'kio-bucket'
#AWS_S3_REGION_NAME = 'us-east-2'
AWS_ACCESS_KEY_ID = get_secret('S3_ACCESS')
AWS_SECRET_ACCESS_KEY = get_secret('S3_SECRET')
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False

ASGI_APPLICATION = 'project.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [os.environ.get('REDIS_URL', 'redis://localhost:6379')],
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CLOUDINARY_STORAGE = {
    'CLOUDINARY_URL': get_secret('C_URL'),
}