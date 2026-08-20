from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.parshas.views import ParshaViewSet, ReadingScheduleViewSet

router = DefaultRouter()
router.register(r'list', ParshaViewSet, basename='parsha')
router.register(r'calendar', ReadingScheduleViewSet, basename='calendar')

urlpatterns = [
    path('', include(router.urls)),
]
