from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from apps.accounts.managers import CustomUserManager

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    permissions = models.JSONField(default=dict, help_text='Permission map: {"resource": ["action1", "action2"]}')
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'roles'
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    bar_mitzvah_date = models.DateField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    invite_code = models.CharField(max_length=10, unique=True, blank=True, null=True, db_index=True)
    referral_code = models.CharField(max_length=20, unique=True, blank=True, null=True, db_index=True)

    # Two-factor authentication (staff only — see apps/accounts/twofactor.py).
    # The secret only counts once totp_confirmed_at is set: an admin who starts
    # enrolment and walks away must not be locked out by a secret their
    # authenticator never actually stored.
    totp_secret = models.CharField(max_length=64, blank=True, default='')
    totp_confirmed_at = models.DateTimeField(null=True, blank=True)
    totp_recovery_codes = models.JSONField(default=list, blank=True)

    # Subscription Fields (RevenueCat)
    is_pro = models.BooleanField(default=False)
    rc_original_app_user_id = models.CharField(max_length=255, blank=True, null=True)
    rc_entitlement_id = models.CharField(max_length=50, blank=True, null=True)
    rc_subscription_status = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. active, expired, trialing")
    rc_expires_date = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = CustomUserManager()

    class Meta:
        verbose_name = 'user'
        indexes = [
            models.Index(fields=['is_active', 'role']),
            models.Index(fields=['email', 'is_active']),
            models.Index(fields=['date_joined'])
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def has_role(self):
        return self.role is not None

    def has_perm_for(self, resource, action):
        if self.is_superuser:
            return True
        if not self.role:
            return False
        res_perms = self.role.permissions.get(resource, [])
        return action in res_perms or '*' in res_perms

    def save(self, *args, **kwargs):
        import uuid
        if not self.invite_code:
            self.invite_code = uuid.uuid4().hex[:8].upper()
        if not self.referral_code:
            self.referral_code = 'REF' + uuid.uuid4().hex[:6].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

class ParentChildLink(models.Model):
    parent = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='children_links')
    child = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='parent_links')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['parent', 'child'], name='unique_parent_child')
        ]

class Referral(models.Model):
    referrer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='referrals_made')
    referred_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='referred_by', null=True, blank=True)
    status = models.CharField(max_length=20, choices=(('invited', 'Invited'), ('subscribed', 'Subscribed')), default='invited')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.referrer.email} referred {self.referred_user.email if self.referred_user else 'Unknown'}"

class CoachingRequest(models.Model):
    COACHING_TYPE_CHOICES = (
        ('in_person', 'In-Person Lessons'),
        ('zoom', 'Zoom Lessons'),
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='coaching_requests')
    name = models.CharField(max_length=255, blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    preferred_times = models.TextField(blank=True, default='', help_text="Preferred times for coaching")
    coaching_type = models.CharField(max_length=20, choices=COACHING_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Coaching request from {self.name} ({self.coaching_type})"

class Feedback(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='feedback_submitted')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.user.email} at {self.created_at}"
