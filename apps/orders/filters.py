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
