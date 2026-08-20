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
