from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.content.views import AudioTrackViewSet, ListeningHistoryViewSet, AdminAudioTrackViewSet, TestimonialViewSet, StudentRecordingViewSet

router = DefaultRouter()
router.register(r'admin-tracks', AdminAudioTrackViewSet, basename='admin-audio-track')
router.register(r'tracks', AudioTrackViewSet, basename='audio-track')
router.register(r'history', ListeningHistoryViewSet, basename='listening-history')
router.register(r'listening-history', ListeningHistoryViewSet, basename='listening-history-alias')
router.register(r'testimonials', TestimonialViewSet, basename='testimonial')
router.register(r'student-recordings', StudentRecordingViewSet, basename='student-recording')
urlpatterns = [
    path('', include(router.urls)),
]
