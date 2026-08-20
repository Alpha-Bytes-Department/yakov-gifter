import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def write_file(path, content):
    full_path = BASE_DIR / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"Created: {path}")

def run():
    write_file(".gitignore", """
.env
.venv/
venv/
env/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env.bak/
venv.bak/
db.sqlite3
db.sqlite3-journal
media/
staticfiles/
.pytest_cache/
.coverage
htmlcov/
*.log
""")

    write_file("config/__init__.py", """
from config.celery import app as celery_app
__all__ = ('celery_app',)
""")

    write_file("config/celery.py", """
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
""")

    write_file("config/settings/__init__.py", """
import os
from decouple import config

DJANGO_ENV = config('DJANGO_ENV', default='development')

if DJANGO_ENV == 'production':
    from .production import *
else:
    from .development import *
""")

    write_file("config/settings/base.py", """
from pathlib import Path
from decouple import config
from datetime import timedelta
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'django_celery_beat',
    # Local
    'apps.core',
    'apps.accounts',
    'apps.categories',
    'apps.products',
    'apps.orders',
]

AUTH_USER_MODEL = 'accounts.CustomUser'

MIDDLEWARE = [
    'apps.core.middleware.RequestIDMiddleware',
    'apps.core.middleware.RequestLoggingMiddleware',
    'apps.core.middleware.ResponseTimeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.SecurityHeadersMiddleware',
    'apps.core.middleware.GlobalExceptionMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

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
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.StandardPageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'apps.core.renderers.StandardJSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'apps.core.throttling.BurstRateThrottle',
        'apps.core.throttling.SustainedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'burst': '60/min',
        'sustained': '1000/day',
        'auth': '5/min',
    },
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler'
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
""")

    write_file("config/settings/development.py", """
from .base import *

DEBUG = True
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE.insert(MIDDLEWARE.index('django.middleware.common.CommonMiddleware') + 1, 'debug_toolbar.middleware.DebugToolbarMiddleware')
INTERNAL_IPS = ['127.0.0.1']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'burst': '600/min',
    'sustained': '10000/day',
    'auth': '50/min',
}
""")

    write_file("config/settings/production.py", """
from .base import *

DEBUG = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Security Headers
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Static files
MIDDLEWARE.insert(MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
""")

    write_file("config/urls.py", """
from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('apps.accounts.urls')),
    path('api/v1/categories/', include('apps.categories.urls')),
    path('api/v1/products/', include('apps.products.urls')),
    path('api/v1/orders/', include('apps.orders.urls')),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    except ImportError:
        pass
""")

    write_file("config/wsgi.py", """
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()
""")

    write_file("config/asgi.py", """
import os
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_asgi_application()
""")

    write_file("apps/__init__.py", "")
    write_file("apps/core/__init__.py", "")
    
    write_file("apps/core/apps.py", """
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
""")

    write_file("apps/core/models.py", """
from django.db import models

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']
""")

    write_file("apps/core/pagination.py", """
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination, CursorPagination
from rest_framework.response import Response

class StandardPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Success',
            'data': data,
            'meta': {
                'pagination': {
                    'count': self.page.paginator.count,
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link(),
                    'current_page': self.page.number,
                    'total_pages': self.page.paginator.num_pages
                }
            }
        })

class StandardLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Success',
            'data': data,
            'meta': {
                'pagination': {
                    'count': self.count,
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link(),
                    'limit': self.limit,
                    'offset': self.offset
                }
            }
        })

class StandardCursorPagination(CursorPagination):
    page_size = 20
    ordering = '-created_at'
    
    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Success',
            'data': data,
            'meta': {
                'pagination': {
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link()
                }
            }
        })
""")

    write_file("apps/core/renderers.py", """
from rest_framework.renderers import JSONRenderer

class StandardJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context and renderer_context['response'].status_code >= 400:
            if isinstance(data, dict) and 'success' in data:
                return super().render(data, accepted_media_type, renderer_context)
            response_data = {
                'success': False,
                'status_code': renderer_context['response'].status_code,
                'message': 'Error',
                'errors': data,
                'data': None
            }
            return super().render(response_data, accepted_media_type, renderer_context)
            
        if isinstance(data, dict) and 'success' in data:
            return super().render(data, accepted_media_type, renderer_context)
            
        response_data = {
            'success': True,
            'status_code': 200,
            'message': 'Success',
            'data': data,
            'meta': {}
        }
        return super().render(response_data, accepted_media_type, renderer_context)
""")

    write_file("apps/core/exceptions.py", """
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
import logging

logger = logging.getLogger('apps')

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            'success': False,
            'status_code': response.status_code,
            'message': str(exc),
            'errors': response.data,
            'data': None
        }
    else:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return response
""")

    write_file("apps/core/middleware.py", """
import uuid
import time
import logging
from django.http import JsonResponse

logger = logging.getLogger('apps')

class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.id = str(uuid.uuid4())
        response = self.get_response(request)
        response['X-Request-ID'] = request.id
        return response

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        logger.info(f"Method: {request.method} Path: {request.path} Status: {response.status_code} IP: {request.META.get('REMOTE_ADDR')}")
        return response

class ResponseTimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time
        response['X-Response-Time-Ms'] = int(duration * 1000)
        if duration > 0.5:
            logger.warning(f"Slow request: {request.path} took {duration:.2f}s")
        return response

class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

class GlobalExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as e:
            logger.error(f"Global exception: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'status_code': 500,
                'message': 'Internal Server Error',
                'errors': str(e) if request.META.get('DJANGO_ENV') == 'development' else 'An unexpected error occurred.',
                'data': None
            }, status=500)
""")

    write_file("apps/core/permissions.py", """
from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return hasattr(obj, 'user') and obj.user == request.user or hasattr(obj, 'created_by') and obj.created_by == request.user

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class IsActiveUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_active
""")

    write_file("apps/core/throttling.py", """
from rest_framework.throttling import UserRateThrottle

class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'

class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'

class AuthRateThrottle(UserRateThrottle):
    scope = 'auth'
""")

    write_file("apps/core/cache.py", """
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.response import Response

def cache_key_generator(prefix, *args, **kwargs):
    key = f"{prefix}:" + ":".join([str(a) for a in args])
    for k, v in kwargs.items():
        key += f":{k}={v}"
    return key

def invalidate_model_cache(model_name):
    # This requires a cache backend that supports pattern matching like Redis
    try:
        cache.delete_pattern(f"*{model_name}*")
    except AttributeError:
        pass

class CacheResponseMixin:
    @method_decorator(cache_page(60 * 15))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 15))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
        
    def perform_create(self, serializer):
        super().perform_create(serializer)
        invalidate_model_cache(self.queryset.model.__name__.lower())
        
    def perform_update(self, serializer):
        super().perform_update(serializer)
        invalidate_model_cache(self.queryset.model.__name__.lower())
        
    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        invalidate_model_cache(self.queryset.model.__name__.lower())
""")

    write_file("apps/core/utils.py", """
from django.utils.text import slugify

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def generate_unique_slug(model_class, value, slug_field='slug'):
    slug = slugify(value)
    unique_slug = slug
    num = 1
    while model_class.objects.filter(**{slug_field: unique_slug}).exists():
        unique_slug = f'{slug}-{num}'
        num += 1
    return unique_slug

def normalize_email(email):
    return email.strip().lower() if email else ''
""")

if __name__ == '__main__':
    run()
