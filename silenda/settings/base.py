
"""
Django settings for silenda project.

Generated by 'django-admin startproject' using Django 3.0.7.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os

HUNT_LABEL = '2021-hunt'

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HUNT_DIR = os.path.join(BASE_DIR, HUNT_LABEL)
import sys
sys.path.insert(0, HUNT_DIR)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '<SECRET_KEY>'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    'localhost',
    '.ue.r.appspot.com',
    'perpendicular.institute',
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'silenda',
    'corsheaders',
    'puzzleviewer',
    'hunt',
    'spoilr',
    'channels',
    'nuntius',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'silenda.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(HUNT_DIR, 'top'),
            os.path.join(HUNT_DIR),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'silenda.wsgi.application'
ASGI_APPLICATION = 'silenda.routing.application'

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
STATICFILES_DIRS = [
    os.path.join(HUNT_DIR, "static"),
]

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "static")
PUZZLE_DATA = '2021-hunt/puzzle'
PUZZLE_EXTRAS_DATA = '2021-hunt/puzzle_extras'
UNLOCK_EXTRAS_DATA = '2021-hunt/unlock_extras'
ROUND_DATA = '2021-hunt/round'

POSTHUNT = True
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
        "CONFIG": {
            #"capacity": 1000,
        },
    }
}

SECRET_AUTH = '<Secret Auth Token>'

PRELOAD_INFINITE = False

# Webhook URLS
DISCORD_WEBHOOK_DEFAULT = ''
DISCORD_WEBHOOK_PUZZLE = ''
DISCORD_WEBHOOK_HINT = ''
DISCORD_WEBHOOK_EMAIL = ''
DISCORD_WEBHOOK_QUEUE = ''
DISCORD_WEBHOOKS = {
    'round-access': None,
    'puzzle-access': None,
    'puzzle-solved': DISCORD_WEBHOOK_PUZZLE,
    'puzzle-incorrect': DISCORD_WEBHOOK_PUZZLE,
    'metapuzzle-access': DISCORD_WEBHOOK_PUZZLE,
    'metapuzzle-solved': DISCORD_WEBHOOK_PUZZLE,
    'metapuzzle-incorrect': DISCORD_WEBHOOK_PUZZLE,
    'interaction': DISCORD_WEBHOOK_DEFAULT,
    'admin-interaction': DISCORD_WEBHOOK_DEFAULT,
    'hint-puzzle': DISCORD_WEBHOOK_HINT,
    'submit-puzzle': None,
    'submit-contact': DISCORD_WEBHOOK_HINT,
    'queue-claim': None,
    'queue-timeout': None,
    'queue-resolution': None,
    'email': DISCORD_WEBHOOK_EMAIL,
    'cafe-luge': DISCORD_WEBHOOK_DEFAULT,
    'queue': DISCORD_WEBHOOK_QUEUE,
}

START_TIME = 1610730000 # 1/15/21 12:00:00 EST
UNLOCK_TIME = 1610733600 # 1/15/21 13:00:00 EST

DEFAULT_DOMAIN = 'perpendicular.institute'
DEFAULT_SENDER = ('HQ', 'hq@%s' % (DEFAULT_DOMAIN))

MAILGUN_API_KEY = '<???>'

USE_PUZZLE_STATIC = False

CLEAR_TEMPEST_URL = '<???>'

CORS_ORIGIN_ALLOW_ALL = False

LANGUAGE_COOKIE_SAMESITE = 'None'
LANGUAGE_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True

USE_PROFILER = False

from corsheaders.signals import check_request_enabled

BYPASS_CORS = ['/get_teams/']
def cors_allow_api_to_everyone(sender, request, **kwargs):
    return request.path in BYPASS_CORS
check_request_enabled.connect(cors_allow_api_to_everyone)

MMO_STATIC_URL = '<Static URL>'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '???',
        'USER': '???',
        'PASSWORD': '???',
        'PORT': '3306',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [{'address':('<REDIS_HOST>', 6379), 'db': 2}],
            "capacity": 1000,
            "expiry": 10,
        },
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://<REDIS_HOST>:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

DATABASES['default']['HOST'] = '<CLOUD_SQL_INSTANCE>'