from django.contrib import admin
from .models import UserFeedback, CoachingRequest


@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'short_comment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'comment_text')

    @admin.display(description='Comment')
    def short_comment(self, obj):
        if len(obj.comment_text) > 50:
            return f"{obj.comment_text[:50]}..."
        return obj.comment_text


@admin.register(CoachingRequest)
class CoachingRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'coaching_type', 'status', 'created_at')
    list_filter = ('coaching_type', 'status', 'created_at')
    search_fields = ('user__email',)
