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
