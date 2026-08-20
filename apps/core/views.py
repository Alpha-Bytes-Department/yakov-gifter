from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.contrib.auth import get_user_model
from django.db.models import Sum
from apps.content.models import AudioTrack
from apps.payments.models import UserSubscription
from django.utils import timezone
from datetime import timedelta
from django.views.generic import TemplateView

User = get_user_model()

class AdminLoginView(TemplateView):
    template_name = 'admin_dashboard/login.html'

class AdminDashboardView(TemplateView):
    template_name = 'admin_dashboard/dashboard.html'

class AdminAnalyticsView(TemplateView):
    template_name = 'admin_dashboard/analytics.html'

class AdminAudioView(TemplateView):
    template_name = 'admin_dashboard/audio-upload.html'

class AdminPaymentsView(TemplateView):
    template_name = 'admin_dashboard/payments.html'

class AdminNotificationsView(TemplateView):
    template_name = 'admin_dashboard/notifications.html'

class AdminSettingsView(TemplateView):
    template_name = 'admin_dashboard/settings.html'

class AdminCoachingView(TemplateView):
    template_name = 'admin_dashboard/coaching.html'

class AdminUsersView(TemplateView):
    template_name = 'admin_dashboard/users.html'

class AdminScheduleView(TemplateView):
    template_name = 'admin_dashboard/schedule.html'

class AdminFeedbackView(TemplateView):
    template_name = 'admin_dashboard/feedback.html'

class AdminTestimonialsView(TemplateView):
    template_name = 'admin_dashboard/testimonials.html'

class AdminDashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        from apps.audio_manager.models import AudioRecording
        from apps.users_and_subs.models import UserProfile
        from apps.interactions.models import CoachingRequest as InterCoachingRequest, UserFeedback as InterUserFeedback
        from django.db.models import Q
        
        now = timezone.now()
        total_users = User.objects.count()
        
        # Pro / Paid Users count from User and UserProfile
        pro_users = User.objects.filter(
            Q(is_pro=True) | 
            Q(profile__subscription_type__in=['Monthly $5', 'Yearly $49']) | 
            Q(profile__has_one_time_purchase_36=True)
        ).distinct().count()
        
        audio_files_count = AudioRecording.objects.count() + AudioTrack.objects.count()
        
        # Calculate revenue from UserProfile subscriptions
        monthly_count = UserProfile.objects.filter(subscription_type='Monthly $5').count()
        yearly_count = UserProfile.objects.filter(subscription_type='Yearly $49').count()
        onetime_count = UserProfile.objects.filter(has_one_time_purchase_36=True).count()
        revenue = (monthly_count * 5) + (yearly_count * 49) + (onetime_count * 36)
        if revenue == 0:
            revenue = pro_users * 5

        # Recent Audio Uploads from AudioRecording
        recent_recordings = AudioRecording.objects.order_by('-created_at')[:10]
        recent_uploads_data = []
        for r in recent_recordings:
            recent_uploads_data.append({
                "id": r.id,
                "title": r.title_english,
                "title_english": r.title_english,
                "title_hebrew": r.title_hebrew,
                "category": r.category,
                "upload_status": "Available" if r.audio_file else "Not Uploaded",
                "audio_file": r.audio_file.url if r.audio_file else None,
                "created_at": r.created_at.isoformat()
            })
        
        if not recent_uploads_data:
            tracks = AudioTrack.objects.order_by('-created_at')[:5]
            for t in tracks:
                recent_uploads_data.append({
                    "id": t.id,
                    "title": t.title,
                    "title_english": t.title,
                    "title_hebrew": "",
                    "category": t.category,
                    "upload_status": "Available" if t.audio_file else "Not Uploaded",
                    "audio_file": t.audio_file.url if t.audio_file else None,
                    "created_at": t.created_at.isoformat()
                })

        # Unified Activity Feed
        activities = []
        for r in recent_recordings[:5]:
            activities.append({
                "type": "audio",
                "color": "blue",
                "title": "Audio Recording:",
                "description": f"{r.title_english} ({r.category}) - {'Available' if r.audio_file else 'Not Uploaded'}",
                "date": r.created_at.isoformat()
            })

        for cr in InterCoachingRequest.objects.order_by('-created_at')[:5]:
            activities.append({
                "type": "coaching",
                "color": "amber",
                "title": "Coaching Request:",
                "description": f"{cr.user.full_name or cr.user.email} requested {cr.coaching_type} ({cr.status})",
                "date": cr.created_at.isoformat()
            })

        for fb in InterUserFeedback.objects.order_by('-created_at')[:5]:
            activities.append({
                "type": "feedback",
                "color": "violet",
                "title": "User Feedback:",
                "description": f"From {fb.user.full_name or fb.user.email}: '{fb.comment_text[:40]}...'",
                "date": fb.created_at.isoformat()
            })

        recent_users = User.objects.order_by('-date_joined')[:5]
        for u in recent_users:
            sub_type = getattr(getattr(u, 'profile', None), 'subscription_type', 'Free')
            activities.append({
                "type": "user",
                "color": "green",
                "title": f"User Joined ({sub_type}):",
                "description": f"{u.full_name or u.email} joined",
                "date": u.date_joined.isoformat()
            })

        activities.sort(key=lambda x: x['date'], reverse=True)
        recent_activity = activities[:8]

        data = {
            "total_users": total_users,
            "pro_subscribers": pro_users,
            "audio_files": audio_files_count,
            "revenue": revenue,
            "coaching_requests_count": InterCoachingRequest.objects.count(),
            "feedback_count": InterUserFeedback.objects.count(),
            "recent_uploads": recent_uploads_data,
            "recent_activity": recent_activity
        }
        
        return Response(data)

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        from apps.content.models import ListeningHistory
        from apps.payments.models import UserSubscription
        from apps.audio_manager.models import AudioRecording
        from apps.users_and_subs.models import UserProfile
        from django.db.models import Count
        
        now = timezone.now()
        months_labels = []
        user_growth = []
        revenue_trend = []
        plays_trend = []
        
        for i in range(5, -1, -1):
            first_day_of_month = (now.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            if first_day_of_month.month == 12:
                next_month = first_day_of_month.replace(year=first_day_of_month.year + 1, month=1, day=1)
            else:
                next_month = first_day_of_month.replace(month=first_day_of_month.month + 1, day=1)
                
            months_labels.append(first_day_of_month.strftime('%b'))
            
            users_count = User.objects.filter(date_joined__gte=first_day_of_month, date_joined__lt=next_month).count()
            user_growth.append(users_count)
            
            # Monthly revenue calculations
            monthly_m = UserProfile.objects.filter(user__date_joined__gte=first_day_of_month, user__date_joined__lt=next_month, subscription_type='Monthly $5').count() * 5
            yearly_m = UserProfile.objects.filter(user__date_joined__gte=first_day_of_month, user__date_joined__lt=next_month, subscription_type='Yearly $49').count() * 49
            onetime_m = UserProfile.objects.filter(user__date_joined__gte=first_day_of_month, user__date_joined__lt=next_month, has_one_time_purchase_36=True).count() * 36
            revenue_trend.append(monthly_m + yearly_m + onetime_m)
            
            plays_count = ListeningHistory.objects.filter(created_at__gte=first_day_of_month, created_at__lt=next_month).count()
            plays_trend.append(plays_count)

        audio_data = {
            "Chumash (Parshios)": AudioRecording.objects.filter(category='Chumash (Parshios)').count(),
            "Mon-Thurs Lainings": AudioRecording.objects.filter(category='Mon-Thurs Lainings').count(),
            "Haftoros": AudioRecording.objects.filter(category='Haftoros').count(),
            "Megillos": AudioRecording.objects.filter(category='Megillos').count(),
            "Nusach HaTefilla": AudioRecording.objects.filter(category='Nusach HaTefilla').count(),
            "Yomim Tovim / Special Lainings": AudioRecording.objects.filter(category='Yomim Tovim / Special Lainings').count(),
        }

        # Payment status distribution
        payment_data = {
            "Free": UserProfile.objects.filter(subscription_type='Free').count(),
            "Monthly $5": UserProfile.objects.filter(subscription_type='Monthly $5').count(),
            "Yearly $49": UserProfile.objects.filter(subscription_type='Yearly $49').count(),
            "$36 One-time Pass": UserProfile.objects.filter(has_one_time_purchase_36=True).count(),
        }

        data = {
            "months": months_labels,
            "revenue": revenue_trend,
            "users": user_growth,
            "audio": audio_data,
            "payments": payment_data,
            "plays": plays_trend
        }
        return Response(data)

    @action(detail=False, methods=['get', 'patch'], url_path=r'coaching_requests(?:/(?P<request_id>\d+))?')
    def coaching_requests(self, request, request_id=None):
        from apps.interactions.models import CoachingRequest as InterCoachingRequest
        from apps.accounts.models import CoachingRequest as AccCoachingRequest
        from apps.interactions.serializers import CoachingRequestSerializer
        
        if request.method == 'PATCH' and request_id:
            from django.shortcuts import get_object_or_404
            try:
                coaching_req = InterCoachingRequest.objects.get(id=request_id)
            except InterCoachingRequest.DoesNotExist:
                coaching_req = get_object_or_404(AccCoachingRequest, id=request_id)
            
            if 'status' in request.data:
                coaching_req.status = request.data['status']
                coaching_req.save()
            return Response({'status': 'updated', 'id': coaching_req.id})

        inter_qs = list(InterCoachingRequest.objects.all().order_by('-created_at'))
        results = CoachingRequestSerializer(inter_qs, many=True).data

        # Fallback for accounts CoachingRequest
        acc_qs = AccCoachingRequest.objects.all().order_by('-created_at')
        for item in acc_qs:
            results.append({
                "id": item.id,
                "user": None,
                "user_email": item.email,
                "user_name": item.name or item.email,
                "phone": item.phone or '',
                "coaching_type": item.coaching_type,
                "status": getattr(item, 'status', 'Pending'),
                "created_at": item.created_at.isoformat()
            })

        return Response(results)

    @action(detail=False, methods=['get', 'post'], url_path='audio_recordings')
    def audio_recordings(self, request):
        from apps.audio_manager.models import AudioRecording
        from apps.audio_manager.serializers import AudioRecordingSerializer
        
        if request.method == 'POST':
            serializer = AudioRecordingSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # Combine both AudioRecording and AudioTrack into a unified list
        results = []
        
        # AudioRecording entries (from audio_manager)
        for r in AudioRecording.objects.all().order_by('-created_at'):
            results.append({
                'id': r.id,
                'source': 'recording',
                'title_english': r.title_english,
                'title_hebrew': r.title_hebrew or '',
                'category': r.category,
                'audio_file': r.audio_file.url if r.audio_file else None,
                'upload_status': 'Available' if r.audio_file else 'Not Uploaded',
                'created_at': r.created_at.isoformat(),
            })
        
        # AudioTrack entries (from content) — the bulk of the 550 tracks
        CATEGORY_DISPLAY = {
            'chumash': 'Chumash (Parshios)',
            'mon_thu': 'Mon-Thurs Lainings',
            'haftoros': 'Haftoros',
            'megillos': 'Megillos',
            'nusach': 'Nusach HaTefilla',
            'yomim_tovim': 'Yomim Tovim / Special Lainings',
        }
        for t in AudioTrack.objects.all().order_by('-created_at'):
            results.append({
                'id': f'track-{t.id}',
                'source': 'track',
                'title_english': t.title,
                'title_hebrew': '',
                'category': CATEGORY_DISPLAY.get(t.category, t.category),
                'audio_file': t.audio_file.url if t.audio_file else None,
                'upload_status': 'Available' if t.audio_file else 'Not Uploaded',
                'created_at': t.created_at.isoformat(),
            })
        
        return Response(results)

    @action(detail=False, methods=['delete'], url_path=r'audio_recordings/(?P<recording_id>\d+)')
    def delete_audio_recording(self, request, recording_id=None):
        from django.shortcuts import get_object_or_404
        from apps.audio_manager.models import AudioRecording
        rec = get_object_or_404(AudioRecording, id=recording_id)
        rec.delete()
        return Response({'status': 'deleted', 'id': recording_id})

    @action(detail=False, methods=['get'])
    def users(self, request):
        from apps.accounts.serializers import AdminUserListSerializer
        qs = User.objects.all().order_by('-date_joined')
        return Response(AdminUserListSerializer(qs, many=True).data)

    @action(detail=False, methods=['patch'], url_path=r'users/(?P<user_id>\d+)')
    def edit_user(self, request, user_id=None):
        from django.shortcuts import get_object_or_404
        from apps.accounts.serializers import AdminUserListSerializer
        from apps.users_and_subs.models import UserProfile
        
        user = get_object_or_404(User, id=user_id)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        if 'is_pro' in request.data:
            user.is_pro = str(request.data['is_pro']).lower() in ['true', '1']
        user.save()

        if 'subscription_type' in request.data:
            profile.subscription_type = request.data['subscription_type']
            if profile.subscription_type in ['Monthly $5', 'Yearly $49']:
                user.is_pro = True
                user.save(update_fields=['is_pro'])
        if 'has_one_time_purchase_36' in request.data:
            profile.has_one_time_purchase_36 = str(request.data['has_one_time_purchase_36']).lower() in ['true', '1']
        if 'date_of_birth' in request.data and request.data['date_of_birth']:
            profile.date_of_birth = request.data['date_of_birth']
        if 'referral_count' in request.data:
            profile.referral_count = int(request.data['referral_count'])
            
        profile.save()
        return Response(AdminUserListSerializer(user).data)

    @action(detail=False, methods=['post'], url_path=r'users/(?P<user_id>\d+)/apply_reward')
    def apply_referral_reward(self, request, user_id=None):
        from django.shortcuts import get_object_or_404
        from apps.users_and_subs.models import UserProfile
        from apps.accounts.serializers import AdminUserListSerializer
        
        user = get_object_or_404(User, id=user_id)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        
        if profile.referral_count >= 3:
            profile.subscription_type = 'Monthly $5'
            profile.save()
            user.is_pro = True
            user.save(update_fields=['is_pro'])
            return Response({'status': 'success', 'message': 'Applied 1 Month Free Reward for 3+ referrals!'})
        else:
            return Response({'status': 'failed', 'message': f'User only has {profile.referral_count} referral(s). Needs 3+ referrals.'}, status=status.HTTP_400_BAD_REQUEST)

from apps.core.models import AdminNotification, SiteSettings
from apps.core.serializers import AdminNotificationSerializer, SiteSettingsSerializer

class AdminNotificationViewSet(viewsets.ModelViewSet):
    queryset = AdminNotification.objects.all()
    serializer_class = AdminNotificationSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        # Dummy logic: Set recipients based on audience
        instance = serializer.save()
        if instance.audience == 'all':
            instance.recipients_count = User.objects.count()
        elif instance.audience == 'pro':
            instance.recipients_count = User.objects.filter(is_pro=True).count()
        else:
            instance.recipients_count = User.objects.filter(is_pro=False).count()
        instance.save()

from rest_framework.permissions import IsAuthenticated
from django.db import models

class UserNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdminNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = AdminNotification.objects.filter(is_active=True)
        if user.is_pro:
            return qs.filter(models.Q(audience='all') | models.Q(audience='pro'))
        else:
            return qs.filter(models.Q(audience='all') | models.Q(audience='free'))

class SiteSettingsViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]
    
    def list(self, request):
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(settings)
        data = serializer.data
        data['admin_profile'] = {
            'name': request.user.full_name or f"{request.user.first_name} {request.user.last_name}".strip() or "Admin User",
            'email': request.user.email,
            'role': request.user.role.name if hasattr(request.user, 'role') and request.user.role else "Super Admin"
        }
        return Response(data)
        
    def create(self, request):
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        admin_profile = request.data.get('admin_profile')
        if admin_profile:
            if 'name' in admin_profile:
                parts = admin_profile['name'].split(' ')
                request.user.last_name = parts.pop() if len(parts) > 1 else ''
                request.user.first_name = ' '.join(parts)
            if 'email' in admin_profile:
                request.user.email = admin_profile['email']
            request.user.save()
            
        data = serializer.data
        data['admin_profile'] = {
            'name': request.user.full_name or f"{request.user.first_name} {request.user.last_name}".strip() or "Admin User",
            'email': request.user.email,
            'role': request.user.role.name if hasattr(request.user, 'role') and request.user.role else "Super Admin"
        }
        return Response(data)

    @action(detail=False, methods=['get'], url_path='feedback_list')
    def feedback_list(self, request):
        from apps.interactions.models import UserFeedback as InterUserFeedback
        from apps.accounts.models import Feedback as AccFeedback
        
        search = request.query_params.get('search', '').strip()
        data = []
        
        inter_qs = InterUserFeedback.objects.select_related('user').order_by('-created_at')
        if search:
            inter_qs = inter_qs.filter(user__email__icontains=search) | InterUserFeedback.objects.filter(comment_text__icontains=search).order_by('-created_at')
            
        for f in inter_qs.distinct():
            data.append({
                'id': f.id,
                'email': f.user.email if f.user else '',
                'name': f.user.full_name or f.user.email if f.user else 'Anonymous',
                'message': f.comment_text,
                'created_at': f.created_at.isoformat(),
            })
            
        acc_qs = AccFeedback.objects.select_related('user').order_by('-created_at')
        if search:
            acc_qs = acc_qs.filter(user__email__icontains=search) | AccFeedback.objects.filter(message__icontains=search).order_by('-created_at')
            
        for f in acc_qs.distinct():
            data.append({
                'id': f.id,
                'email': f.user.email if f.user else '',
                'name': f.user.full_name or f.user.email if f.user else 'Anonymous',
                'message': f.message,
                'created_at': f.created_at.isoformat(),
            })
            
        return Response({'results': data, 'count': len(data)})

    @action(detail=False, methods=['get'], url_path='testimonials_list')
    def testimonials_list(self, request):
        from apps.content.models import Testimonial
        search = request.query_params.get('search', '').strip()
        status_filter = request.query_params.get('status', '').strip()
        
        qs = Testimonial.objects.all().order_by('-created_at')
        if search:
            qs = qs.filter(author_name__icontains=search) | qs.filter(content__icontains=search)
        if status_filter:
            if status_filter == 'approved':
                qs = qs.filter(is_approved=True)
            elif status_filter == 'pending':
                qs = qs.filter(is_approved=False)
            
        data = []
        for t in qs:
            data.append({
                'id': t.id,
                'name': t.author_name,
                'designation': 'User',
                'text': t.content,
                'status': 'approved' if t.is_approved else 'pending',
                'rating': 5,
                'created_at': t.created_at.isoformat(),
            })
        return Response({'results': data, 'count': len(data)})

    @action(detail=False, methods=['patch'], url_path=r'testimonials/(?P<testimonial_id>\d+)')
    def edit_testimonial(self, request, testimonial_id=None):
        from django.shortcuts import get_object_or_404
        from apps.content.models import Testimonial
        testimonial = get_object_or_404(Testimonial, id=testimonial_id)
        
        if 'status' in request.data:
            testimonial.is_approved = (request.data['status'] == 'approved')
            testimonial.save()
            
        return Response({'id': testimonial.id, 'status': 'approved' if testimonial.is_approved else 'pending'})
