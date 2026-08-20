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
    write_file("apps/categories/__init__.py", "")

    write_file("apps/categories/apps.py", """
from django.apps import AppConfig

class CategoriesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.categories'
""")

    write_file("apps/categories/models.py", """
from django.db import models
from apps.core.models import TimeStampedModel
from apps.core.utils import generate_unique_slug

class Category(TimeStampedModel):
    name = models.CharField(max_length=200, unique=True, db_index=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['is_active', 'sort_order']),
            models.Index(fields=['parent', 'is_active'])
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Category, self.name)
        super().save(*args, **kwargs)
        
    @property
    def full_path(self):
        path = [self.name]
        curr = self.parent
        while curr is not None:
            path.append(curr.name)
            curr = curr.parent
        return ' > '.join(reversed(path))
""")

    write_file("apps/categories/serializers.py", """
from rest_framework import serializers
from apps.categories.models import Category

class CategoryListSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'parent', 'image', 'sort_order', 'is_active', 'product_count')

class CategoryDetailSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'parent', 'parent_detail', 'image', 'sort_order', 'is_active', 'children')

    def get_children(self, obj):
        # Prevent deep recursion
        request = self.context.get('request')
        depth = self.context.get('depth', 1)
        if depth > 3:
            return []
        children = obj.children.filter(is_active=True)
        return CategoryDetailSerializer(children, many=True, context={'request': request, 'depth': depth + 1}).data

    def get_parent_detail(self, obj):
        if obj.parent:
            return {
                'id': obj.parent.id,
                'name': obj.parent.name,
                'slug': obj.parent.slug
            }
        return None

class CategoryCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('name', 'description', 'parent', 'image', 'sort_order', 'is_active')

    def validate_parent(self, value):
        if self.instance and value:
            # prevent circular reference
            if self.instance == value:
                raise serializers.ValidationError("Category cannot be its own parent")
            curr = value
            while curr:
                if curr == self.instance:
                    raise serializers.ValidationError("Circular reference detected in category hierarchy")
                curr = curr.parent
        return value
""")

    write_file("apps/categories/filters.py", """
from django_filters import rest_framework as filters
from apps.categories.models import Category

class CategoryFilter(filters.FilterSet):
    is_active = filters.BooleanFilter()
    parent = filters.NumberFilter()
    is_root = filters.BooleanFilter(field_name='parent', lookup_expr='isnull')
    name = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Category
        fields = ['is_active', 'parent', 'is_root', 'name']
""")

    write_file("apps/categories/views.py", """
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
""")

    write_file("apps/categories/admin.py", """
from django.contrib import admin
from apps.categories.models import Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'sort_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'parent']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['sort_order', 'is_active']
""")

    write_file("apps/categories/urls.py", """
from rest_framework.routers import DefaultRouter
from apps.categories.views import CategoryViewSet

router = DefaultRouter()
router.register(r'', CategoryViewSet, basename='categories')
urlpatterns = router.urls
""")

    write_file("apps/categories/tests/__init__.py", "")

    # PRODUCTS APP

    write_file("apps/products/__init__.py", "")
    write_file("apps/products/apps.py", """
from django.apps import AppConfig

class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.products'
""")

    write_file("apps/products/models.py", """
from django.db import models
from django.conf import settings
from django.db.models import Q
from apps.core.models import TimeStampedModel
from apps.categories.models import Category
from apps.core.utils import generate_unique_slug

class Product(TimeStampedModel):
    name = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=300, unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    barcode = models.CharField(max_length=100, blank=True, db_index=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_products')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_featured', 'is_active']),
            models.Index(fields=['price', 'is_active']),
            models.Index(fields=['category', 'price']),
            models.Index(fields=['-created_at', 'is_active']),
        ]
        constraints = [
            models.CheckConstraint(check=Q(price__gte=0), name='product_price_non_negative'),
            models.CheckConstraint(check=Q(stock_quantity__gte=0), name='product_stock_non_negative')
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Product, self.name)
        super().save(*args, **kwargs)

    @property
    def is_on_sale(self):
        return self.compare_at_price is not None and self.compare_at_price > self.price

    @property
    def discount_percentage(self):
        if self.is_on_sale:
            return int((self.compare_at_price - self.price) / self.compare_at_price * 100)
        return 0

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    @property
    def is_low_stock(self):
        return 0 < self.stock_quantity <= self.low_stock_threshold

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    sort_order = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ['sort_order']
        indexes = [models.Index(fields=['product', 'sort_order'])]
""")

    write_file("apps/products/serializers.py", """
from rest_framework import serializers
from apps.products.models import Product, ProductImage

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'alt_text', 'sort_order', 'is_primary')

class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'short_description', 'price', 'compare_at_price',
            'is_on_sale', 'discount_percentage', 'category_name', 'primary_image',
            'is_in_stock', 'is_featured'
        )

    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first() or obj.images.first()
        if image:
            return self.context['request'].build_absolute_uri(image.image.url)
        return None

class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = Product
        fields = '__all__'

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        exclude = ('created_by',)

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative")
        return value
""")

    write_file("apps/products/filters.py", """
from django_filters import rest_framework as filters
from apps.products.models import Product

class ProductFilter(filters.FilterSet):
    category = filters.NumberFilter()
    category_slug = filters.CharFilter(field_name='category__slug')
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    is_featured = filters.BooleanFilter()
    is_in_stock = filters.BooleanFilter(method='filter_in_stock')
    name = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Product
        fields = ['category', 'category_slug', 'min_price', 'max_price', 'is_featured', 'name']

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock_quantity__gt=0)
        return queryset.filter(stock_quantity=0)
""")

    write_file("apps/products/views.py", """
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
""")

    write_file("apps/products/admin.py", """
from django.contrib import admin
from apps.products.models import Product, ProductImage

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'sku', 'stock_quantity', 'is_active', 'is_featured']
    list_filter = ['is_active', 'is_featured', 'category']
    search_fields = ['name', 'sku']
    prepopulated_fields = {'slug': ('name',)}
    list_select_related = ['category', 'created_by']
    inlines = [ProductImageInline]
""")

    write_file("apps/products/urls.py", """
from rest_framework.routers import DefaultRouter
from apps.products.views import ProductViewSet

router = DefaultRouter()
router.register(r'', ProductViewSet, basename='products')
urlpatterns = router.urls
""")

    write_file("apps/products/tests/__init__.py", "")

if __name__ == '__main__':
    run()
