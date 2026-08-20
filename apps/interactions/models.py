from django.db import models
from django.conf import settings


class UserFeedback(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='interaction_feedbacks'
    )
    comment_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User Feedback'
        verbose_name_plural = 'User Feedbacks'

    def __str__(self):
        return f"Feedback from {self.user} on {self.created_at.strftime('%Y-%m-%d')}"


class CoachingRequest(models.Model):
    COACHING_TYPE_CHOICES = [
        ('In-person Staten Island', 'In-person Staten Island'),
        ('In-person Brooklyn', 'In-person Brooklyn'),
        ('Zoom worldwide', 'Zoom worldwide'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Contacted', 'Contacted'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='interaction_coaching_requests'
    )
    coaching_type = models.CharField(
        max_length=100,
        choices=COACHING_TYPE_CHOICES
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Coaching Request'
        verbose_name_plural = 'Coaching Requests'

    def __str__(self):
        return f"Coaching ({self.coaching_type}) for {self.user} - {self.status}"
