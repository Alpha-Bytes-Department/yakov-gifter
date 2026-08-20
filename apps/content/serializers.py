from rest_framework import serializers
from apps.content.models import AudioTrack, ListeningHistory, Testimonial, StudentRecording
from apps.parshas.serializers import ParshaSerializer

from apps.parshas.models import Parsha

class AudioTrackSerializer(serializers.ModelSerializer):
    parsha = ParshaSerializer(read_only=True)
    parsha_id = serializers.PrimaryKeyRelatedField(
        queryset=Parsha.objects.all(),
        source='parsha',
        write_only=True,
        required=False,
        allow_null=True
    )
    is_locked = serializers.SerializerMethodField()
    
    class Meta:
        model = AudioTrack
        fields = ('id', 'title', 'audio_file', 'duration_seconds', 'file_size_bytes', 
                  'category', 'parsha', 'parsha_id', 'segment_type', 'grouping', 'status', 'access_level', 'is_locked', 'created_at')

    def get_is_locked(self, obj):
        request = self.context.get('request')
        if request and request.user:
            # Admins or owner (if applicable) can access, otherwise check is_pro status
            if request.user.is_staff:
                return False
            if obj.access_level == 'pro' and not request.user.is_pro:
                return True
        return False

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # If the track is locked, null out the audio file URL to protect content
        if self.get_is_locked(instance):
            data['audio_file'] = None
        elif instance.audio_file and instance.audio_file.name:
            file_name = str(instance.audio_file.name)
            if file_name.startswith(('http://', 'https://')):
                data['audio_file'] = file_name
            else:
                request = self.context.get('request')
                if request:
                    data['audio_file'] = request.build_absolute_uri(instance.audio_file.url)
                else:
                    data['audio_file'] = instance.audio_file.url
        return data

class ListeningHistorySerializer(serializers.ModelSerializer):
    track = AudioTrackSerializer(read_only=True)
    track_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ListeningHistory
        fields = ('id', 'track', 'track_id', 'last_position_seconds', 'completed', 'updated_at')

    def create(self, validated_data):
        user = self.context['request'].user
        track_id = validated_data.pop('track_id')
        history, created = ListeningHistory.objects.update_or_create(
            user=user,
            track_id=track_id,
            defaults=validated_data
        )
        return history

class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = ('id', 'user', 'author_name', 'content', 'is_approved', 'created_at')
        read_only_fields = ('user', 'is_approved')

class StudentRecordingSerializer(serializers.ModelSerializer):
    track_title = serializers.CharField(source='track.title', read_only=True)
    
    class Meta:
        model = StudentRecording
        fields = ('id', 'user', 'track', 'track_title', 'audio_file', 'duration_seconds', 'status', 'teacher_feedback', 'created_at')
        read_only_fields = ('user', 'status', 'teacher_feedback')
