import datetime
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from apps.parshas.models import Parsha, ReadingSchedule
from apps.parshas.serializers import ParshaSerializer, ReadingScheduleSerializer

class ParshaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ParshaSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['sefer']
    search_fields = ['name', 'name_hebrew', 'sefer']

    def get_queryset(self):
        queryset = Parsha.objects.prefetch_related('audio_tracks').all()
        category = self.request.query_params.get('category')
        if category:
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
            norm = cat_map.get(category.lower().strip(), category.lower().strip())
            queryset = queryset.filter(audio_tracks__category=norm).distinct()
        return queryset

class ReadingScheduleViewSet(viewsets.ModelViewSet):
    queryset = ReadingSchedule.objects.select_related('parsha').all()
    serializer_class = ReadingScheduleSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        
        if month and year:
            queryset = queryset.filter(date__year=year, date__month=month)
            
        return queryset

    @action(detail=False, methods=['get'])
    def next(self, request):
        today = datetime.date.today()
        # Find the next reading date
        schedule = self.get_queryset().filter(date__gte=today).order_by('date').first()
        
        if not schedule:
            return Response({"detail": "No upcoming reading schedule found."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = self.get_serializer(schedule)
        data = serializer.data
        
        # Calculate weeks until bar mitzvah
        bar_mitzvah_date = request.user.bar_mitzvah_date
        
        if not bar_mitzvah_date and request.user.date_of_birth:
            try:
                from pyluach import dates
                # 1. Convert Gregorian DOB to Hebrew date
                heb_dob = dates.GregorianDate.frompydate(request.user.date_of_birth).to_heb()
                # 2. Add 13 Hebrew years
                heb_bm = dates.HebrewDate(heb_dob.year + 13, heb_dob.month, heb_dob.day)
                # 3. Convert back to Gregorian date
                bar_mitzvah_date = heb_bm.to_pydate()
            except Exception as e:
                # Fallback to Gregorian + 13 years if conversion fails
                try:
                    bar_mitzvah_date = request.user.date_of_birth.replace(year=request.user.date_of_birth.year + 13)
                except ValueError:
                    bar_mitzvah_date = request.user.date_of_birth + datetime.timedelta(days=365*13 + 3)
                
        weeks_until = None
        if bar_mitzvah_date:
            delta = bar_mitzvah_date - today
            weeks_until = max(0, delta.days // 7)
            
        data['weeks_until_bar_mitzvah'] = weeks_until
        
        return Response(data)
