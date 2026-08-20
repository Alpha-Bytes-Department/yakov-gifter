from django.contrib import admin
from django.utils.html import format_html
from .models import AudioRecording


@admin.register(AudioRecording)
class AudioRecordingAdmin(admin.ModelAdmin):
    list_display = ('title_english', 'title_hebrew', 'category', 'upload_status')
    list_filter = ('category',)
    search_fields = ('title_english', 'title_hebrew')

    @admin.display(description='Upload Status')
    def upload_status(self, obj):
        if obj.audio_file:
            return format_html('<span style="color: green; font-weight: bold;">Available</span>')
        return format_html('<span style="color: red; font-weight: bold;">Not Uploaded</span>')

