from rest_framework import serializers
from .models import AudioRecording


class AudioRecordingSerializer(serializers.ModelSerializer):
    upload_status = serializers.SerializerMethodField()

    class Meta:
        model = AudioRecording
        fields = ('id', 'title_english', 'title_hebrew', 'category', 'audio_file', 'upload_status', 'created_at')
        read_only_fields = ('id', 'created_at')

    def get_upload_status(self, obj):
        return 'Available' if obj.audio_file else 'Not Uploaded'
