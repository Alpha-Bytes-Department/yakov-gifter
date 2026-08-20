from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
import logging
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger('apps')
User = get_user_model()

@shared_task
def send_welcome_email(user_id):
    try:
        user = User.objects.get(id=user_id)
        send_mail(
            'Welcome to Ezlain',
            f'Hi {user.first_name},\n\nWelcome to Ezlain!',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for welcome email")
    except Exception as e:
        logger.error(f"Failed to send welcome email: {e}")

@shared_task
def send_password_reset_email(user_id, reset_url):
    try:
        user = User.objects.get(id=user_id)
        send_mail(
            'Password Reset',
            f'Click here to reset: {reset_url}',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")

@shared_task
def cleanup_inactive_users():
    threshold = timezone.now() - timedelta(days=30)
    users = User.objects.filter(is_active=False, date_joined__lt=threshold)
    count = users.count()
    users.delete()
    logger.info(f"Cleaned up {count} inactive users")
