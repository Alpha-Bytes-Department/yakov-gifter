from django.contrib import admin
from apps.content.models import AudioTrack, ListeningHistory, Testimonial, StudentRecording

@admin.register(AudioTrack)
class AudioTrackAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'status', 'access_level', 'duration_seconds', 'created_at']
    list_filter = ['category', 'status', 'access_level']
    search_fields = ['title', 'notes']
    ordering = ['-created_at']

@admin.register(ListeningHistory)
class ListeningHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'track', 'last_position_seconds', 'completed', 'updated_at']
    list_filter = ['completed']
    search_fields = ['user__email', 'track__title']
    ordering = ['-updated_at']

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['author_name', 'user', 'is_approved', 'created_at']
    list_filter = ['is_approved']
    search_fields = ['author_name', 'content', 'user__email']
    ordering = ['-created_at']

@admin.register(StudentRecording)
class StudentRecordingAdmin(admin.ModelAdmin):
    list_display = ['user', 'track', 'status', 'duration_seconds', 'created_at']
    list_filter = ['status']
    search_fields = ['user__email', 'track__title']
    ordering = ['-created_at']
