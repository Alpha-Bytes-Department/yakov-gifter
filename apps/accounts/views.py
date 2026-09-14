from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.accounts.serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    UserListSerializer, ChangePasswordSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, LinkChildSerializer
)
from apps.accounts.models import ParentChildLink
from apps.accounts.permissions import IsOwnerOrAdmin
from apps.core.throttling import AuthRateThrottle
from apps.accounts.tasks import send_welcome_email, send_password_reset_email
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import django.contrib.auth.tokens as auth_tokens

User = get_user_model()

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class RegisterView(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer
    throttle_classes = [AuthRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        try:
            send_welcome_email.delay(user.id)
        except Exception:
            pass
        
        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserProfileSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)

class LoginView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = UserLoginSerializer
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        from rest_framework.exceptions import Throttled
        from apps.core.ratelimit import (
            client_ip, is_locked_out, register_failure, reset,
        )

        email = (request.data.get('email') or '').strip()
        ip = client_ip(request)

        # The DRF throttle above counts per address. Lockout also counts per
        # account, so rotating IPs does not reset an attacker's budget against
        # one user's password.
        if is_locked_out(email, ip):
            raise Throttled(detail='Too many attempts. Try again in 15 minutes.')

        serializer = self.get_serializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            register_failure(email, ip)
            serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        reset(email, ip)

        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserProfileSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_200_OK)

class LogoutView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response(status=status.HTTP_205_RESET_CONTENT)
            return Response({"detail": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(generics.UpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ChangePasswordSerializer
    
    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"detail": "Password updated successfully"}, status=status.HTTP_200_OK)

class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['email'] # actually returns user object
        
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = auth_tokens.default_token_generator.make_token(user)
        # Assuming frontend URL
        reset_url = f"http://localhost:3000/reset-password?uid={uid}&token={token}"
        
        try:
            send_password_reset_email.delay(user.id, reset_url)
        except Exception:
            pass
        return Response({"detail": "Password reset email sent"}, status=status.HTTP_200_OK)

class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"detail": "Password has been reset"}, status=status.HTTP_200_OK)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related('role').all()
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'email']
    filterset_fields = ['is_active', 'role']

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserProfileSerializer
        
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(id=self.request.user.id)

    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[IsAuthenticated])
    def me(self, request):
        user = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)
        else:
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def referrals(self, request):
        from apps.accounts.models import Referral
        user = request.user
        referrals_made = Referral.objects.filter(referrer=user)
        
        data = {
            "referral_code": user.referral_code,
            "total_referrals": referrals_made.count(),
            "subscribed_referrals": referrals_made.filter(status='subscribed').count(),
            "friends": [
                {
                    "name": r.referred_user.first_name if r.referred_user else "Pending",
                    "status": r.status
                } for r in referrals_made
            ]
        }
        return Response(data)

    @action(detail=False, methods=['post'])
    def coaching(self, request):
        from apps.accounts.serializers import CoachingRequestSerializer
        serializer = CoachingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        
        # Send email notification to coaching team
        from django.core.mail import send_mail
        from django.conf import settings
        try:
            subject = f"New Personal Coaching Request from {request.user.email}"
            message = (
                f"Name: {serializer.validated_data['name']}\n"
                f"Phone: {serializer.validated_data['phone']}\n"
                f"Email: {serializer.validated_data['email']}\n"
                f"Coaching Type: {serializer.validated_data['coaching_type']}\n"
                f"Preferred Times:\n{serializer.validated_data['preferred_times']}\n"
            )
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                ['coaching@ezlain.com'],
                fail_silently=True
            )
        except Exception:
            pass
            
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def feedback(self, request):
        from apps.accounts.serializers import FeedbackSerializer
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class LinkChildView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = LinkChildSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        child = serializer.validated_data['invite_code'] # the validate method returns the User object
        
        # Link them
        ParentChildLink.objects.get_or_create(parent=request.user, child=child)
        
        return Response({"detail": "Successfully linked to child account"}, status=status.HTTP_200_OK)
