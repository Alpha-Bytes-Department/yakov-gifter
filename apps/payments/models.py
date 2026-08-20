from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel

class SubscriptionPlan(TimeStampedModel):
    name = models.CharField(max_length=100) # e.g. Monthly, Annual
    stripe_price_id = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    interval = models.CharField(max_length=20, choices=(('month', 'Month'), ('year', 'Year')))

    def __str__(self):
        return self.name

class UserSubscription(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='active') # active, past_due, canceled
    current_period_end = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    rc_original_app_user_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.plan.name if self.plan else 'No Plan'}"
