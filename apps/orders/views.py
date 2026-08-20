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
