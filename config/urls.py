from django.contrib import admin
from django.urls import path, include
from django.conf import settings

from django.http import JsonResponse

def api_root(request):
    return JsonResponse({
        "name": "Ezlain API",
        "version": "1.0",
        "status": "operational"
    })

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from apps.core.views import (
    AdminLoginView, AdminDashboardView, AdminAnalyticsView,
    AdminAudioView, AdminPaymentsView, AdminNotificationsView,
    AdminSettingsView, AdminCoachingView, AdminUsersView, AdminScheduleView,
    AdminFeedbackView, AdminTestimonialsView
)

urlpatterns = [
    path('', api_root, name='api-root'),
    path('api/', api_root),
    path('api/v1/', api_root),
    path('admin/', admin.site.urls),
    
    # Swagger API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Custom Admin Dashboard UI
    path('dashboard/login/', AdminLoginView.as_view(), name='admin_dashboard_login'),
    path('dashboard/', AdminDashboardView.as_view(), name='admin_dashboard_overview'),
    path('dashboard/analytics/', AdminAnalyticsView.as_view(), name='admin_dashboard_analytics'),
    path('dashboard/audio/', AdminAudioView.as_view(), name='admin_dashboard_audio'),
    path('dashboard/payments/', AdminPaymentsView.as_view(), name='admin_dashboard_payments'),
    path('dashboard/notifications/', AdminNotificationsView.as_view(), name='admin_dashboard_notifications'),
    path('dashboard/settings/', AdminSettingsView.as_view(), name='admin_dashboard_settings'),
    path('dashboard/coaching/', AdminCoachingView.as_view(), name='admin_dashboard_coaching'),
    path('dashboard/schedule/', AdminScheduleView.as_view(), name='admin_dashboard_schedule'),
    path('dashboard/users/', AdminUsersView.as_view(), name='admin_dashboard_users'),
    path('dashboard/feedback/', AdminFeedbackView.as_view(), name='admin_dashboard_feedback'),
    path('dashboard/testimonials/', AdminTestimonialsView.as_view(), name='admin_dashboard_testimonials'),
    
    path('api/v1/accounts/', include('apps.accounts.urls')),
    path('api/v1/categories/', include('apps.categories.urls')),
    path('api/v1/products/', include('apps.products.urls')),
    path('api/v1/orders/', include('apps.orders.urls')),
    path('api/v1/parshas/', include('apps.parshas.urls')),
    path('api/v1/progress/', include('apps.progress.urls')),
    path('api/v1/content/', include('apps.content.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/core/', include('apps.core.urls')),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
