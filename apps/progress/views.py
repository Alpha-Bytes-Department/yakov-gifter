import datetime
from django.db.models import Count, Q
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from apps.accounts.models import ParentChildLink
from apps.progress.models import LearningProgress
from apps.progress.serializers import LearningProgressSerializer, LearningProgressBulkUpdateSerializer
from apps.parshas.models import Parsha, ReadingSchedule

User = get_user_model()

class ProgressViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_child_user(self, child_id):
        user = self.request.user
        if str(user.id) == str(child_id):
            return user
        # Verify parent-child link
        link = ParentChildLink.objects.filter(parent=user, child_id=child_id).first()
        if link:
            return link.child
        return None

    @action(detail=False, methods=['post'])
    def update_status(self, request):
        serializer = LearningProgressBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        parsha_id = serializer.validated_data['parsha_id']
        segment_type = serializer.validated_data['segment_type']
        new_status = serializer.validated_data['status']
        
        progress, created = LearningProgress.objects.get_or_create(
            user=request.user,
            parsha_id=parsha_id,
            segment_type=segment_type,
            defaults={'status': new_status}
        )
        
        if not created:
            progress.status = new_status
            progress.save()
            
        return Response(LearningProgressSerializer(progress).data)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        child_id = request.query_params.get('child_id')
        if not child_id:
            return Response({"detail": "child_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        child = self.get_child_user(child_id)
        if not child:
            return Response({"detail": "Child not found or not linked to your account."}, status=status.HTTP_404_NOT_FOUND)

        # Overall Progress
        total_aliyos_completed = LearningProgress.objects.filter(
            user=child, 
            status='completed',
            segment_type__startswith='aliya_'
        ).count()
        
        total_haftorah_completed = LearningProgress.objects.filter(
            user=child,
            status='completed',
            segment_type='haftorah'
        ).count()
        
        weeks_until_bar_mitzvah = None
        bm_date = child.bar_mitzvah_date
        if not bm_date and child.date_of_birth:
            try:
                bm_date = child.date_of_birth.replace(year=child.date_of_birth.year + 13)
            except ValueError:
                bm_date = child.date_of_birth + datetime.timedelta(days=365*13 + 3)
                
        if bm_date:
            delta = bm_date - datetime.date.today()
            weeks_until_bar_mitzvah = max(0, delta.days // 7)

        # Calculate Haftorah Progress Percentage
        total_schedules = ReadingSchedule.objects.count()
        haftorah_progress_percent = 0
        if total_schedules > 0:
            haftorah_progress_percent = round((total_haftorah_completed / total_schedules) * 100)

        # Current week progress
        today = datetime.date.today()
        next_shabbos = ReadingSchedule.objects.filter(date__gte=today).order_by('date').first()
        
        current_week_progress = []
        if next_shabbos:
            progress_records = LearningProgress.objects.filter(
                user=child,
                parsha=next_shabbos.parsha
            )
            progress_map = {p.segment_type: p.status for p in progress_records}
            
            for segment_code, segment_label in LearningProgress.SEGMENT_CHOICES:
                current_week_progress.append({
                    "segment_type": segment_code,
                    "label": segment_label,
                    "status": progress_map.get(segment_code, "not_started")
                })
        
        return Response({
            "overall_progress": {
                "weeks_until_bar_mitzvah": weeks_until_bar_mitzvah,
                "total_aliyos_completed": total_aliyos_completed,
                "total_haftorah_completed": total_haftorah_completed,
                "haftorah_progress_percentage": haftorah_progress_percent,
                # Assuming 63 total aliyos as per design (or dynamic based on total parshas * 7)
                "total_aliyos_required": 63 
            },
            "current_week": {
                "parsha": next_shabbos.parsha.name if next_shabbos else None,
                "date": next_shabbos.date if next_shabbos else None,
                "grid": current_week_progress
            }
        })

    @action(detail=False, methods=['get'])
    def history(self, request):
        child_id = request.query_params.get('child_id')
        if not child_id:
            return Response({"detail": "child_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        child = self.get_child_user(child_id)
        if not child:
            return Response({"detail": "Child not found or not linked to your account."}, status=status.HTTP_404_NOT_FOUND)

        # 1. Fetch all reading schedules ordered by date descending (most recent first)
        schedules = ReadingSchedule.objects.select_related('parsha').all().order_by('-date')
        
        # 2. Fetch all progress records for this child
        progress_records = LearningProgress.objects.filter(user=child)
        # Create a nested map: parsha_id -> segment_type -> status
        progress_map = {}
        for p in progress_records:
            if p.parsha_id not in progress_map:
                progress_map[p.parsha_id] = {}
            progress_map[p.parsha_id][p.segment_type] = p.status
            
        # 3. Build history list
        history_list = []
        for s in schedules:
            grid = []
            completed_count = 0
            for segment_code, segment_label in LearningProgress.SEGMENT_CHOICES:
                status_val = progress_map.get(s.parsha.id, {}).get(segment_code, "not_started")
                if status_val == 'completed':
                    completed_count += 1
                grid.append({
                    "segment_type": segment_code,
                    "label": segment_label,
                    "status": status_val
                })
                
            history_list.append({
                "parsha_name": s.parsha.name,
                "date": s.date,
                "completed_segments": completed_count,
                "total_segments": 9,
                "grid": grid
            })
            
        return Response(history_list)

    @action(detail=False, methods=['get'])
    def parsha_progress(self, request):
        parsha_id = request.query_params.get('parsha_id')
        if not parsha_id:
            return Response({"detail": "parsha_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        progress_records = LearningProgress.objects.filter(
            user=request.user,
            parsha_id=parsha_id
        )
        data = {p.segment_type: p.status for p in progress_records}
        return Response({"parsha_id": int(parsha_id), "completed_segments": data})

