from django.db import models
from django.core.cache import cache

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

class AdminNotification(TimeStampedModel):
    title = models.CharField(max_length=255)
    message = models.TextField()
    audience = models.CharField(max_length=50, choices=[
        ('all', 'All Users'),
        ('pro', 'Pro Subscribers'),
        ('free', 'Free Users')
    ], default='all')
    recipients_count = models.IntegerField(default=0)
    
    def __str__(self):
        return self.title

class SiteSettings(TimeStampedModel):
    # Singleton model
    email_reports = models.BooleanField(default=True)
    auto_publish_uploads = models.BooleanField(default=False)
    payment_alerts = models.BooleanField(default=True)
    default_upload_status = models.CharField(max_length=20, default='published', choices=[
        ('draft', 'Draft'),
        ('published', 'Published')
    ])
    library_page_size = models.IntegerField(default=24)
    
    class Meta:
        verbose_name_plural = "Site Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete('site_settings')

    @classmethod
    def get_settings(cls):
        settings = cache.get('site_settings')
        if not settings:
            settings, created = cls.objects.get_or_create(pk=1)
            cache.set('site_settings', settings, timeout=86400)
        return settings
