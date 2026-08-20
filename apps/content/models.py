from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel
from apps.parshas.models import Parsha

class AudioTrack(TimeStampedModel):
    CATEGORY_CHOICES = (
        ('chumash', 'Chumash'),
        ('mon_thu', 'Mon-Thu'),
        ('haftoros', 'Haftoros'),
        ('megillos', 'Megillos'),
        ('nusach', 'Nusach'),
        ('yomim_tovim', 'Yomim Tovim'),
    )
    
    STATUS_CHOICES = (
        ('published', 'Published'),
        ('draft', 'Draft'),
        ('processing', 'Processing'),
    )
    
    ACCESS_CHOICES = (
        ('free', 'Free'),
        ('pro', 'Pro'),
    )
    
    title = models.CharField(max_length=255)
    audio_file = models.FileField(upload_to='audio/')
    duration_seconds = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    parsha = models.ForeignKey(Parsha, on_delete=models.SET_NULL, null=True, blank=True, related_name='audio_tracks')
    segment_type = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., Aliya 1, Full, etc.")
    grouping = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., Yamim Noraim, Shalosh Regalim, etc.")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    access_level = models.CharField(max_length=20, choices=ACCESS_CHOICES, default='pro')
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class ListeningHistory(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listening_history')
    track = models.ForeignKey(AudioTrack, on_delete=models.CASCADE, related_name='history')
    last_position_seconds = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'track')

    def __str__(self):
        return f"{self.user.email} - {self.track.title} - {self.last_position_seconds}s"

class Testimonial(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='testimonials')
    author_name = models.CharField(max_length=255, help_text="Name to display (can be different from user's real name)")
    content = models.TextField()
    is_approved = models.BooleanField(default=False, help_text="Set to True to display on the app's home screen")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Testimonial by {self.author_name} - {'Approved' if self.is_approved else 'Pending'}"

class StudentRecording(TimeStampedModel):
    STATUS_CHOICES = (
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recordings')
    track = models.ForeignKey(AudioTrack, on_delete=models.CASCADE, related_name='student_recordings')
    audio_file = models.FileField(upload_to='student_recordings/')
    duration_seconds = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    teacher_feedback = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Recording by {self.user.email} for {self.track.title}"
