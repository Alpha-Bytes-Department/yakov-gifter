from django.db import models
from apps.core.models import TimeStampedModel

class Parsha(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    name_hebrew = models.CharField(max_length=100)
    sefer = models.CharField(max_length=50) # e.g. Bereshit, Shemot
    chapter_verse = models.CharField(max_length=50) # e.g. 26:3 - 27:34
    haftorah_info = models.CharField(max_length=200) # e.g. Yirmiyahu 16:19 - 17:14

    class Meta:
        verbose_name_plural = 'parshas'
        ordering = ['id']

    def __str__(self):
        return self.name

class ReadingSchedule(TimeStampedModel):
    date = models.DateField(unique=True, db_index=True)
    hebrew_date = models.CharField(max_length=100, blank=True, null=True)
    parsha = models.ForeignKey(Parsha, on_delete=models.CASCADE, related_name='schedules')

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.date} - {self.parsha.name}"
