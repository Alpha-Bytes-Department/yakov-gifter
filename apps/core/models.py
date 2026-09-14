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
    # A snapshot taken when the notification is created or its audience changes,
    # not a live figure. That is why the dashboard showed 50 and 100 recipients
    # against an install with five users: those rows were written once, by hand
    # or at a different time, and never revisited.
    # `manage.py recount_notifications` repairs existing rows.
    recipients_count = models.IntegerField(default=0, editable=False)

    def audience_queryset(self):
        """The users this notification is aimed at."""
        from django.contrib.auth import get_user_model
        from django.db.models import Q

        users = get_user_model().objects.all()
        if self.audience == 'all':
            return users

        # "Pro" must mean the same here as on the analytics page, which counts a
        # paid profile as well as the is_pro flag.
        paid = (
            Q(is_pro=True)
            | Q(profile__subscription_type__in=['Monthly $5', 'Yearly $49'])
            | Q(profile__has_one_time_purchase_36=True)
        )

        if self.audience == 'pro':
            return users.filter(paid).distinct()
        return users.exclude(paid).distinct()

    def recount_recipients(self, save=True):
        self.recipients_count = self.audience_queryset().count()
        if save:
            self.save(update_fields=['recipients_count'])
        return self.recipients_count

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
    # The settings page offered a timezone control that was never persisted —
    # it had no field to save into, so it reset to the hardcoded default on
    # every load. That default was the development team's zone, which is why
    # the client kept seeing Asia/Dhaka on his own dashboard.
    timezone = models.CharField(max_length=64, default='America/New_York')
    
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
