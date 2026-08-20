from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel
from apps.parshas.models import Parsha

class LearningProgress(TimeStampedModel):
    STATUS_CHOICES = (
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )

    SEGMENT_CHOICES = (
        ('aliya_1', 'Aliya 1'),
        ('aliya_2', 'Aliya 2'),
        ('aliya_3', 'Aliya 3'),
        ('aliya_4', 'Aliya 4'),
        ('aliya_5', 'Aliya 5'),
        ('aliya_6', 'Aliya 6'),
        ('aliya_7', 'Aliya 7'),
        ('maftir', 'Maftir'),
        ('haftorah', 'Haftorah'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='learning_progress')
    parsha = models.ForeignKey(Parsha, on_delete=models.CASCADE, related_name='learning_progress')
    segment_type = models.CharField(max_length=20, choices=SEGMENT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')

    class Meta:
        verbose_name_plural = 'learning progresses'
        constraints = [
            models.UniqueConstraint(fields=['user', 'parsha', 'segment_type'], name='unique_user_parsha_segment')
        ]

    def __str__(self):
        return f"{self.user.email} - {self.parsha.name} - {self.segment_type} - {self.status}"
