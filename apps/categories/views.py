from rest_framework import viewsets
from django.db.models import Count
from apps.categories.models import Category
from apps.categories.serializers import (
    CategoryListSerializer, CategoryDetailSerializer, CategoryCreateUpdateSerializer
)
from apps.core.permissions import IsAdminOrReadOnly
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.categories.filters import CategoryFilter
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.cache import CacheResponseMixin

class CategoryViewSet(CacheResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CategoryFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'sort_order', 'created_at']

    def get_queryset(self):
        queryset = Category.objects.select_related('parent').prefetch_related('children')
        if self.action == 'list':
            return queryset.annotate(product_count=Count('products'))
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return CategoryListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return CategoryCreateUpdateSerializer
        return CategoryDetailSerializer

    @action(detail=False)
    def tree(self, request):
        roots = self.get_queryset().filter(parent__isnull=True, is_active=True)
        serializer = CategoryDetailSerializer(roots, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True)
    def products(self, request, pk=None):
        category = self.get_object()
        products = category.products.filter(is_active=True)
        # Import dynamically to avoid circular import if needed
        from apps.products.serializers import ProductListSerializer
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)
