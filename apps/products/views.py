from rest_framework import viewsets
from apps.products.models import Product
from apps.products.serializers import (
    ProductListSerializer, ProductDetailSerializer, ProductCreateUpdateSerializer
)
from apps.core.permissions import IsAdminOrReadOnly
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.products.filters import ProductFilter
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.cache import CacheResponseMixin

class ProductViewSet(CacheResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['price', 'name', 'created_at', 'stock_quantity']

    def get_queryset(self):
        # N+1 Optimization: select_related for FKs, prefetch_related for reverse relations
        return Product.objects.select_related('category', 'created_by').prefetch_related('images').filter(is_active=True)

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False)
    def featured(self, request):
        products = self.get_queryset().filter(is_featured=True)
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, url_path='by-category/(?P<category_slug>[-\w]+)')
    def by_category(self, request, category_slug=None):
        products = self.get_queryset().filter(category__slug=category_slug)
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, permission_classes=[IsAdminOrReadOnly])
    def low_stock(self, request):
        if not request.user.is_staff:
            return Response({'detail': 'Not permitted'}, status=403)
        # Using F expression to compare fields
        from django.db.models import F
        products = self.get_queryset().filter(stock_quantity__lte=F('low_stock_threshold'), stock_quantity__gt=0)
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)
