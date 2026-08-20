from rest_framework import serializers
from .models import UserProfile, UserProgress


class UserProfileSerializer(serializers.ModelSerializer):
    weeks_until_bar_mitzvah = serializers.ReadOnlyField()
    referred_by_email = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = (
            'id', 'user', 'stripe_customer_id', 'subscription_type',
            'has_one_time_purchase_36', 'date_of_birth', 'weeks_until_bar_mitzvah',
            'referred_by', 'referred_by_email', 'referral_count'
        )
        read_only_fields = ('id', 'weeks_until_bar_mitzvah', 'referred_by_email')

    def get_referred_by_email(self, obj):
        if obj.referred_by and obj.referred_by.user:
            return obj.referred_by.user.email
        return None


class UserProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProgress
        fields = ('id', 'user', 'audio_recording', 'is_completed', 'completed_at')
