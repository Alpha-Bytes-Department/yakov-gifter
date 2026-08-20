from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.accounts.models import Role

User = get_user_model()

@receiver(post_save, sender=User)
def assign_default_role(sender, instance, created, **kwargs):
    if created and not instance.role:
        try:
            default_role = Role.objects.get(is_default=True)
            instance.role = default_role
            instance.save(update_fields=['role'])
        except Role.DoesNotExist:
            pass
