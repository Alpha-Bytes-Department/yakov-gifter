from rest_framework import viewsets, mixins, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.content.models import AudioTrack, ListeningHistory, Testimonial, StudentRecording
from apps.content.serializers import AudioTrackSerializer, ListeningHistorySerializer, TestimonialSerializer, StudentRecordingSerializer

class AdminAudioTrackViewSet(viewsets.ModelViewSet):
    queryset = AudioTrack.objects.all()
    serializer_class = AudioTrackSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'parsha', 'access_level', 'status']
    search_fields = ['title', 'segment_type']
    ordering_fields = ['created_at', 'title']

class AudioTrackViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AudioTrackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['parsha', 'access_level']
    search_fields = ['title', 'segment_type']
    ordering_fields = ['created_at', 'title']

    def get_queryset(self):
        queryset = AudioTrack.objects.filter(status='published')
        raw_category = self.request.query_params.get('category')
        if raw_category:
            cat_map = {
                'chumash': 'chumash',
                'mon–thurs': 'mon_thu',
                'mon-thurs': 'mon_thu',
                'mon_thu': 'mon_thu',
                'haftoros': 'haftoros',
                'megillos': 'megillos',
                'nusach': 'nusach',
                'yomim tovim': 'yomim_tovim',
                'yomim_tovim': 'yomim_tovim',
            }
            normalized = cat_map.get(raw_category.lower().strip(), raw_category.lower().strip())
            queryset = queryset.filter(category=normalized)
        return queryset

class ListeningHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = ListeningHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['track_id']
    
    def get_queryset(self):
        return ListeningHistory.objects.filter(user=self.request.user).order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TestimonialViewSet(viewsets.ModelViewSet):
    serializer_class = TestimonialSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        # Only show approved testimonials
        return Testimonial.objects.filter(is_approved=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user if self.request.user.is_authenticated else None)

class StudentRecordingViewSet(viewsets.ModelViewSet):
    serializer_class = StudentRecordingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        # Students can only see their own recordings, admins see all
        if self.request.user.is_staff:
            return StudentRecording.objects.all()
        return StudentRecording.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
