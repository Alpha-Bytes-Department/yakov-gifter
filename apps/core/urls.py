from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.core.views import AdminDashboardViewSet, AdminNotificationViewSet, SiteSettingsViewSet, UserNotificationViewSet

router = DefaultRouter()
router.register(r'admin', AdminDashboardViewSet, basename='admin-dashboard')
router.register(r'admin/notifications', AdminNotificationViewSet, basename='admin-notifications')
router.register(r'admin/settings', SiteSettingsViewSet, basename='admin-settings')
router.register(r'notifications', UserNotificationViewSet, basename='user-notifications')

urlpatterns = [
    path('', include(router.urls)),
]
