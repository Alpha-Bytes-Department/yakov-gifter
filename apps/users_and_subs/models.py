from django.db import models
from django.conf import settings
from django.utils import timezone


class UserProfile(models.Model):
    SUBSCRIPTION_CHOICES = [
        ('Free', 'Free'),
        ('Monthly $5', 'Monthly $5'),
        ('Yearly $49', 'Yearly $49'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    subscription_type = models.CharField(
        max_length=50,
        choices=SUBSCRIPTION_CHOICES,
        default='Free'
    )
    has_one_time_purchase_36 = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)
    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals'
    )
    referral_count = models.IntegerField(default=0)

    @property
    def weeks_until_bar_mitzvah(self):
        if not self.date_of_birth:
            return None
        today = timezone.now().date()
        try:
            thirteenth_birthday = self.date_of_birth.replace(year=self.date_of_birth.year + 13)
        except ValueError:
            thirteenth_birthday = self.date_of_birth.replace(year=self.date_of_birth.year + 13, day=28)
        
        days_remaining = (thirteenth_birthday - today).days
        return days_remaining // 7

    def __str__(self):
        return f"{self.user} - {self.subscription_type}"


from apps.audio_manager.models import AudioRecording


class UserProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='progress'
    )
    audio_recording = models.ForeignKey(
        AudioRecording,
        on_delete=models.CASCADE,
        related_name='user_progress'
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Progress'
        verbose_name_plural = 'User Progresses'

    def __str__(self):
        status = "Completed" if self.is_completed else "In Progress"
        return f"{self.user} - {self.audio_recording.title_english} ({status})"


