from rest_framework import serializers
from apps.parshas.models import Parsha, ReadingSchedule

class ParshaSerializer(serializers.ModelSerializer):
    loaded_tracks_count = serializers.SerializerMethodField()
    total_duration_seconds = serializers.SerializerMethodField()
    is_loaded = serializers.SerializerMethodField()

    class Meta:
        model = Parsha
        fields = ('id', 'name', 'name_hebrew', 'sefer', 'chapter_verse', 'haftorah_info', 
                  'loaded_tracks_count', 'total_duration_seconds', 'is_loaded')

    def get_loaded_tracks_count(self, obj):
        return obj.audio_tracks.filter(status='published').count()

    def get_total_duration_seconds(self, obj):
        from django.db.models import Sum
        result = obj.audio_tracks.filter(status='published').aggregate(total=Sum('duration_seconds'))
        return result['total'] or 0

    def get_is_loaded(self, obj):
        return obj.audio_tracks.filter(status='published').exists()

class ReadingScheduleSerializer(serializers.ModelSerializer):
    parsha = ParshaSerializer(read_only=True)
    parsha_id = serializers.PrimaryKeyRelatedField(
        queryset=Parsha.objects.all(), source='parsha', write_only=True
    )
    
    class Meta:
        model = ReadingSchedule
        fields = ('id', 'date', 'hebrew_date', 'parsha', 'parsha_id')
