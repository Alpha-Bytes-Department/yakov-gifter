from rest_framework import serializers
from apps.payments.models import SubscriptionPlan, UserSubscription

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'

class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True, default='No Plan')
    plan_price = serializers.DecimalField(source='plan.price', max_digits=6, decimal_places=2, read_only=True, default=0.00)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = UserSubscription
        fields = ('id', 'user', 'user_email', 'plan_name', 'plan_price', 'status', 'current_period_end', 'created_at')
