import os
from decouple import config

DJANGO_ENV = config('DJANGO_ENV', default='development')

if DJANGO_ENV == 'production':
    from .production import *
else:
    from .development import *
