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
    write_file("apps/orders/__init__.py", "")
    write_file("apps/orders/apps.py", """
from django.apps import AppConfig

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.orders'
""")

    write_file("apps/orders/models.py", """
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel
from apps.products.models import Product
import uuid
import random
from django.utils import timezone

ORDER_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('processing', 'Processing'),
    ('shipped', 'Shipped'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
    ('refunded', 'Refunded')
]

PAYMENT_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('paid', 'Paid'),
    ('failed', 'Failed'),
    ('refunded', 'Refunded')
]

class Order(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, db_index=True, editable=False)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending', db_index=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_address = models.TextField()
    billing_address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['order_number']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['payment_status', 'status']),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            date_str = timezone.now().strftime('%Y%m%d')
            random_suffix = str(random.randint(10000, 99999))
            self.order_number = f"ORD-{date_str}-{random_suffix}"
        super().save(*args, **kwargs)

    def calculate_totals(self):
        items = self.items.all()
        self.subtotal = sum(item.total_price for item in items)
        # simplistic calculation
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_amount
        self.save(update_fields=['subtotal', 'total_amount'])

    def can_cancel(self):
        return self.status in ['pending', 'confirmed']

    def can_transition_to(self, new_status):
        valid_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered', 'returned'],
            'delivered': ['returned'],
            'cancelled': [],
            'refunded': []
        }
        return new_status in valid_transitions.get(self.status, [])

    @property
    def is_paid(self):
        return self.payment_status == 'paid'
        
    @property
    def item_count_val(self):
        # We try to use annotated value if available, else query
        return getattr(self, 'item_count', self.items.count())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    product_name = models.CharField(max_length=300)
    product_sku = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        indexes = [models.Index(fields=['order', 'product'])]
        constraints = [models.UniqueConstraint(fields=['order', 'product'], name='unique_order_product')]

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
""")

    write_file("apps/orders/serializers.py", """
from rest_framework import serializers
from django.db import transaction
from django.db.models import F
from apps.orders.models import Order, OrderItem
from apps.products.models import Product

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_name', 'product_sku', 'quantity', 'unit_price', 'total_price')
        read_only_fields = ('product_name', 'product_sku', 'unit_price', 'total_price')

class OrderItemCreateSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        product = attrs['product']
        quantity = attrs['quantity']
        if product.stock_quantity < quantity:
            raise serializers.ValidationError(f"Not enough stock for product {product.name}. Available: {product.stock_quantity}")
        return attrs

class OrderListSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(source='item_count_val', read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'order_number', 'status', 'payment_status', 'total_amount', 'item_count', 'created_at')

class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Order
        fields = '__all__'

class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemCreateSerializer(many=True)
    shipping_address = serializers.CharField()
    billing_address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must have at least one item.")
        # Ensure unique products
        product_ids = [item['product'].id for item in value]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError("Duplicate products in order are not allowed.")
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user
        
        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                shipping_address=validated_data['shipping_address'],
                billing_address=validated_data.get('billing_address', ''),
                notes=validated_data.get('notes', '')
            )
            
            for item_data in items_data:
                product = item_data['product']
                quantity = item_data['quantity']
                
                # Double check stock with select_for_update to lock the row
                locked_product = Product.objects.select_for_update().get(id=product.id)
                if locked_product.stock_quantity < quantity:
                    raise serializers.ValidationError(f"Product {product.name} went out of stock.")
                    
                # Deduct stock safely
                locked_product.stock_quantity = F('stock_quantity') - quantity
                locked_product.save(update_fields=['stock_quantity'])
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_sku=product.sku,
                    quantity=quantity,
                    unit_price=product.price
                )
                
            order.calculate_totals()
            
            # send_order_confirmation_email.delay(order.id) (Assuming imported)
            
        return order

class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.ORDER_STATUS_CHOICES)
""")

    write_file("apps/orders/filters.py", """
from django_filters import rest_framework as filters
from apps.orders.models import Order

class OrderFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=Order.ORDER_STATUS_CHOICES)
    payment_status = filters.ChoiceFilter(choices=Order.PAYMENT_STATUS_CHOICES)
    min_total = filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    max_total = filters.NumberFilter(field_name='total_amount', lookup_expr='lte')
    date_from = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    date_to = filters.DateFilter(field_name='created_at', lookup_expr='lte')
    user = filters.NumberFilter()

    class Meta:
        model = Order
        fields = ['status', 'payment_status', 'user']
""")

    write_file("apps/orders/views.py", """
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from apps.orders.models import Order, OrderItem
from apps.orders.serializers import (
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer, OrderStatusUpdateSerializer
)
from apps.orders.filters import OrderFilter
from apps.core.permissions import IsOwner

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrderFilter
    search_fields = ['order_number', 'shipping_address']
    ordering_fields = ['created_at', 'total_amount', 'status']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        # Optimization
        queryset = Order.objects.select_related('user').prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        ).annotate(item_count=Count('items'))
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return OrderListSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        elif self.action in ['confirm', 'ship', 'deliver', 'cancel']:
            return OrderStatusUpdateSerializer
        return OrderDetailSerializer

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'detail': 'Not permitted'}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        if not order.can_transition_to('confirmed'):
            return Response({'detail': 'Invalid transition'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'confirmed'
        order.save()
        return Response({'status': 'confirmed'})

    @action(detail=True, methods=['post'])
    def ship(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'detail': 'Not permitted'}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        if not order.can_transition_to('shipped'):
            return Response({'detail': 'Invalid transition'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'shipped'
        order.shipped_at = timezone.now()
        order.save()
        return Response({'status': 'shipped'})

    @action(detail=True, methods=['post'])
    def deliver(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'detail': 'Not permitted'}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        if not order.can_transition_to('delivered'):
            return Response({'detail': 'Invalid transition'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'delivered'
        order.delivered_at = timezone.now()
        order.save()
        return Response({'status': 'delivered'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if not request.user.is_staff and order.user != request.user:
            return Response({'detail': 'Not permitted'}, status=status.HTTP_403_FORBIDDEN)
        if not order.can_cancel():
            return Response({'detail': 'Order cannot be cancelled'}, status=status.HTTP_400_BAD_REQUEST)
            
        from django.db import transaction
        from django.db.models import F
        
        with transaction.atomic():
            order.status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.save()
            # restore stock
            for item in order.items.all():
                product = item.product
                product.stock_quantity = F('stock_quantity') + item.quantity
                product.save(update_fields=['stock_quantity'])
                
        return Response({'status': 'cancelled'})

    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        queryset = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = OrderListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = OrderListSerializer(queryset, many=True)
        return Response(serializer.data)
""")

    write_file("apps/orders/tasks.py", """
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from apps.orders.models import Order
import logging

logger = logging.getLogger('apps')

@shared_task
def send_order_confirmation_email(order_id):
    try:
        order = Order.objects.select_related('user').get(id=order_id)
        send_mail(
            f'Order Confirmation {order.order_number}',
            f'Thank you for your order! Total amount: {order.total_amount}',
            settings.EMAIL_HOST_USER,
            [order.user.email],
            fail_silently=False,
        )
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")

@shared_task
def generate_daily_sales_report():
    logger.info("Generating daily sales report...")
""")

    write_file("apps/orders/admin.py", """
from django.contrib import admin
from apps.orders.models import Order, OrderItem
from django.db.models import Count

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ['product_name', 'product_sku', 'unit_price', 'total_price']
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'payment_status', 'total_amount', 'item_count', 'created_at']
    list_filter = ['status', 'payment_status', 'created_at']
    search_fields = ['order_number', 'user__email']
    readonly_fields = ['order_number', 'subtotal', 'total_amount']
    list_select_related = ['user']
    inlines = [OrderItemInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(item_count=Count('items'))

    def item_count(self, obj):
        return getattr(obj, 'item_count', obj.items.count())
    item_count.short_description = 'Items'
""")

    write_file("apps/orders/urls.py", """
from rest_framework.routers import DefaultRouter
from apps.orders.views import OrderViewSet

router = DefaultRouter()
router.register(r'', OrderViewSet, basename='orders')
urlpatterns = router.urls
""")

    write_file("apps/orders/tests/__init__.py", "")

    # Deployment
    write_file("Dockerfile", """
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \\
    libpq-dev gcc netcat-traditional && \\
    rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--config", "gunicorn.conf.py"]
""")

    write_file("docker-compose.yml", """
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${DB_NAME:-ezlain_db}
      POSTGRES_USER: ${DB_USER:-ezlain_user}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-ezlain_pass}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ezlain_user"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - ezlain-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - ezlain-network

  web:
    build: .
    command: ./entrypoint.sh gunicorn config.wsgi:application -c gunicorn.conf.py
    volumes:
      - .:/app
      - static_files:/app/staticfiles
      - media_files:/app/media
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - ezlain-network

  celery_worker:
    build: .
    command: ./celery_entrypoint.sh celery -A config worker -l info
    volumes:
      - .:/app
      - media_files:/app/media
    env_file:
      - .env
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - ezlain-network

  celery_beat:
    build: .
    command: ./celery_entrypoint.sh celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - ezlain-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf
      - static_files:/app/staticfiles
      - media_files:/app/media
    depends_on:
      - web
    networks:
      - ezlain-network

volumes:
  postgres_data:
  redis_data:
  static_files:
  media_files:

networks:
  ezlain-network:
    driver: bridge
""")

    write_file("nginx/nginx.conf", """
upstream web_app {
    server web:8000;
}

server {
    listen 80;
    server_name localhost;
    client_max_body_size 10M;

    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /app/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://web_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }
}
""")

    write_file("gunicorn.conf.py", """
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 120
graceful_timeout = 30
keepalive = 5

bind = '0.0.0.0:8000'
backlog = 2048

accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

proc_name = 'ezlain_backend'
daemon = False
preload_app = True

max_requests = 1000
max_requests_jitter = 50
""")

    write_file("entrypoint.sh", """#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --no-input

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Starting Gunicorn..."
exec "$@"
""")

    write_file("celery_entrypoint.sh", """#!/bin/bash
set -e

echo "Starting Celery..."
exec "$@"
""")

    write_file("README.md", """
# Ezlain Backend
Production-ready Django REST API

## Features
- JWT Auth, RBAC
- Product Catalog & Categories
- Orders & Inventory management
- Docker Deployment
""")

if __name__ == '__main__':
    run()
