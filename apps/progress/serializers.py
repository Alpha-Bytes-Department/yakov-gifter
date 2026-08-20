from rest_framework import serializers
from apps.progress.models import LearningProgress
from apps.parshas.serializers import ParshaSerializer

class LearningProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningProgress
        fields = ('id', 'user', 'parsha', 'segment_type', 'status', 'updated_at')
        read_only_fields = ('id', 'user', 'updated_at')

class LearningProgressBulkUpdateSerializer(serializers.Serializer):
    parsha_id = serializers.IntegerField(required=True)
    segment_type = serializers.ChoiceField(choices=LearningProgress.SEGMENT_CHOICES, required=True)
    status = serializers.ChoiceField(choices=LearningProgress.STATUS_CHOICES, required=True)
