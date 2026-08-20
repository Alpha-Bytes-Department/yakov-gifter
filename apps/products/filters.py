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
