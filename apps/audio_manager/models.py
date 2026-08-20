from django.db import models


class AudioRecording(models.Model):
    CATEGORY_CHOICES = [
        ('Chumash (Parshios)', 'Chumash (Parshios)'),
        ('Mon-Thurs Lainings', 'Mon-Thurs Lainings'),
        ('Yomim Tovim / Special Lainings', 'Yomim Tovim / Special Lainings'),
        ('Haftoros', 'Haftoros'),
        ('Megillos', 'Megillos'),
        ('Nusach HaTefilla', 'Nusach HaTefilla'),
    ]

    title_english = models.CharField(max_length=255)
    title_hebrew = models.CharField(max_length=255, blank=True, default='')
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    audio_file = models.FileField(upload_to='audio_recordings/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title_english} - {self.category}"
