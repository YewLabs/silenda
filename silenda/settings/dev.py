from silenda.settings.base import *

DEBUG = True
STATIC_URL = '/static/'

LANGUAGE_COOKIE_SAMESITE = 'Lax'
LANGUAGE_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = False

SECURE_PROXY_SSL_HEADER = None
SECURE_SSL_REDIRECT = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '???',
        'USER': '???',
        'PASSWORD': '???',
        'PORT': '5432',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

USE_PUZZLE_STATIC = True
USE_PROFILER = False
#CACHES['default']['LOCATION'] = 'redis://127.0.0.1:6379/1'
#CHANNEL_LAYERS['default']['CONFIG']['hosts'][0]['address'] = ('127.0.0.1', 6379)
DISCORD_WEBHOOK_DEFAULT = None
DISCORD_WEBHOOKS = {
}

MAILGUN_API_KEY = ''

#POSTHUNT = True
