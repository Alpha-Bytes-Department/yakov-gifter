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
