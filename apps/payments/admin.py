from django.contrib import admin
from apps.payments.models import SubscriptionPlan, UserSubscription

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'stripe_price_id', 'price', 'interval']
    list_filter = ['interval']
    search_fields = ['name']

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'current_period_end']
    list_filter = ['status', 'plan']
    search_fields = ['user__email']
