from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.payments.views import PaymentViewSet, AdminPaymentViewSet

router = DefaultRouter()
router.register(r'admin', AdminPaymentViewSet, basename='admin-payments')
router.register(r'', PaymentViewSet, basename='payments')

urlpatterns = [
    path('', include(router.urls)),
]
