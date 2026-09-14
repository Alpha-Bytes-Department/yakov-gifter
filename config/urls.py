from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.generic import TemplateView

from decouple import config

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from apps.core.views import (
    AdminLoginView, AdminDashboardView, AdminAnalyticsView,
    AdminAudioView, AdminPaymentsView, AdminNotificationsView,
    AdminSettingsView, AdminCoachingView, AdminUsersView, AdminScheduleView,
    AdminFeedbackView, AdminTestimonialsView,
    DashboardSessionLoginView, DashboardSessionLogoutView,
)


def api_root(request):
    return JsonResponse({
        "name": "Ezlain API",
        "version": "1.0",
        "status": "operational"
    })


def robots_txt(request):
    # The API and dashboard should never be indexed.
    lines = [
        'User-agent: *',
        'Disallow: /api/',
        'Disallow: /dashboard/',
        f'Disallow: /{config("DJANGO_ADMIN_PATH", default="admin/")}',
        'Allow: /$',
        '',
        f'Sitemap: {config("SITE_URL", default="https://ezlain.app")}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')


def sitemap_xml(request):
    site = config('SITE_URL', default='https://ezlain.app')
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'<url><loc>{site}/</loc><priority>1.0</priority></url>'
        '</urlset>'
    )
    return HttpResponse(body, content_type='application/xml')


# The default /admin/ path is the first thing a scanner tries. Moving it is not
# a security control on its own, but it removes the free hit.
DJANGO_ADMIN_PATH = config('DJANGO_ADMIN_PATH', default='admin/')

urlpatterns = [
    # A public landing page rather than raw API JSON.
    path('', TemplateView.as_view(template_name='public/landing.html'), name='landing'),
    path('robots.txt', robots_txt, name='robots'),
    path('sitemap.xml', sitemap_xml, name='sitemap'),

    path('api/', api_root),
    path('api/v1/', api_root),
    path(DJANGO_ADMIN_PATH, admin.site.urls),

    # Custom Admin Dashboard UI
    path('dashboard/login/', AdminLoginView.as_view(), name='admin_dashboard_login'),
    path('dashboard/session-login/', DashboardSessionLoginView.as_view(), name='admin_dashboard_session_login'),
    path('dashboard/session-logout/', DashboardSessionLogoutView.as_view(), name='admin_dashboard_session_logout'),
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

# The OpenAPI schema documents every endpoint, its parameters and its auth
# requirements — a free map of the attack surface. Keep it available where it is
# useful (local development, and to a signed-in staff user) and closed otherwise.
if settings.DEBUG or config('EXPOSE_API_DOCS', cast=bool, default=False):
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
