from django.contrib import admin
from apps.progress.models import LearningProgress

@admin.register(LearningProgress)
class LearningProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'parsha', 'segment_type', 'status', 'updated_at']
    list_filter = ['status', 'segment_type']
    search_fields = ['user__email', 'parsha__name']
    ordering = ['-updated_at']
