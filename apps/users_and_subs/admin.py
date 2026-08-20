from django.contrib import admin
from .models import UserProfile, UserProgress


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'subscription_type',
        'stripe_customer_id',
        'has_one_time_purchase_36',
        'date_of_birth',
        'weeks_until_bar_mitzvah',
        'referral_count',
    )
    list_filter = ('subscription_type', 'has_one_time_purchase_36')
    search_fields = ('user__email', 'stripe_customer_id')
    actions = ['apply_one_month_free_reward']

    @admin.action(description="Apply 1 month free reward for 3+ referrals")
    def apply_one_month_free_reward(self, request, queryset):
        eligible = queryset.filter(referral_count__gte=3)
        updated_count = eligible.update(subscription_type='Monthly $5')
        self.message_user(
            request,
            f"Successfully applied 1 Month Free Reward to {updated_count} user(s) with 3+ referrals."
        )


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'audio_recording', 'is_completed', 'completed_at')
    list_filter = ('user', 'audio_recording__category', 'is_completed')
    search_fields = (
        'user__email',
        'audio_recording__title_english',
        'audio_recording__title_hebrew',
    )

