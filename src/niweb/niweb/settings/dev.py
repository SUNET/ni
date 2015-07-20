# -*- coding: utf-8 -*-
__author__ = 'lundberg'

"""Development settings and globals."""

from os import environ
import dotenv
import json
from common import *

# Read .env from project root
dotenv.read_dotenv(join(SITE_ROOT, '.devenv'))

########## PROJECT CONFIGURATION
# Neo4j settings
NEO4J_RESOURCE_URI = environ.get('NEO4J_RESOURCE_URI', 'http://localhost:7474')
NEO4J_MAX_DATA_AGE = environ.get('NEO4J_MAX_DATA_AGE', '24')  # hours

# To be able to use the report mailing functionality you need to set a to address and a key.
REPORTS_TO = environ['REPORTS_TO'].split()
REPORTS_CC = environ.get('REPORTS_CC', '').split()     # Optional
REPORTS_BCC = environ.get('REPORTS_BCC', '').split()   # Optional
# EXTRA_REPORT_TO = {'ID': ['address', ]}
EXTRA_REPORT_TO = json.loads(environ.get('EXTRA_REPORT_TO', '{}'))  # Optional
REPORT_KEY = environ['REPORT_KEY']

########## END PROJECT CONFIGURATION

########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': environ.get('DB_ENGINE', 'django.db.backends.postgresql_psycopg2'),
        'NAME': environ.get('DB_NAME', 'norduni'),
        'USER': environ.get('DB_USER', 'ni'),
        'PASSWORD': environ.get('DB_PASSWORD', 'docker'),
        'HOST': environ.get('DB_HOST', 'localhost'),
        'PORT': environ.get('DB_PORT', '5432')
    }
}
########## END DATABASE CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION

########## TOOLBAR CONFIGURATION
# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INSTALLED_APPS += (
    'debug_toolbar',
)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INTERNAL_IPS = ('127.0.0.1',)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
MIDDLEWARE_CLASSES += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

DEBUG_TOOLBAR_CONFIG = {}
########## END TOOLBAR CONFIGURATION