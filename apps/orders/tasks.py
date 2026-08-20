from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from apps.orders.models import Order
import logging

logger = logging.getLogger('apps')

@shared_task
def send_order_confirmation_email(order_id):
    try:
        order = Order.objects.select_related('user').get(id=order_id)
        send_mail(
            f'Order Confirmation {order.order_number}',
            f'Thank you for your order! Total amount: {order.total_amount}',
            settings.EMAIL_HOST_USER,
            [order.user.email],
            fail_silently=False,
        )
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")

@shared_task
def generate_daily_sales_report():
    logger.info("Generating daily sales report...")
