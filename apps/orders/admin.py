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
