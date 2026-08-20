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
