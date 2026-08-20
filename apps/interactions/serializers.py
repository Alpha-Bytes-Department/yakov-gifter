from rest_framework import serializers
from .models import UserFeedback, CoachingRequest


class UserFeedbackSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = UserFeedback
        fields = ('id', 'user', 'user_email', 'user_name', 'comment_text', 'created_at')
        read_only_fields = ('id', 'created_at', 'user_email', 'user_name')

    def get_user_email(self, obj):
        return obj.user.email if obj.user else ''

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.full_name or obj.user.email
        return ''


class CoachingRequestSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = CoachingRequest
        fields = ('id', 'user', 'user_email', 'user_name', 'phone', 'coaching_type', 'status', 'created_at')
        read_only_fields = ('id', 'created_at', 'user_email', 'user_name', 'phone')

    def get_user_email(self, obj):
        return obj.user.email if obj.user else ''

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.full_name or obj.user.email
        return ''

    def get_phone(self, obj):
        if obj.user:
            return getattr(obj.user, 'phone', '') or ''
        return ''
