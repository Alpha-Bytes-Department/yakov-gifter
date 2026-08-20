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
