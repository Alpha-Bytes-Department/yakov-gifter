import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def write_file(path, content):
    full_path = BASE_DIR / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"Created: {path}")

def run():
    write_file("manage.py", """
#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django."
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
""")

    write_file("apps/accounts/__init__.py", "")

    write_file("apps/accounts/apps.py", """
from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'

    def ready(self):
        import apps.accounts.signals
""")

    write_file("apps/accounts/managers.py", """
from django.contrib.auth.models import BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email=email)
""")

    write_file("apps/accounts/models.py", """
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from apps.accounts.managers import CustomUserManager

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    permissions = models.JSONField(default=dict, help_text='Permission map: {"resource": ["action1", "action2"]}')
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'roles'
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = CustomUserManager()

    class Meta:
        verbose_name = 'user'
        indexes = [
            models.Index(fields=['is_active', 'role']),
            models.Index(fields=['email', 'is_active']),
            models.Index(fields=['date_joined'])
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def has_role(self):
        return self.role is not None

    def has_perm_for(self, resource, action):
        if self.is_superuser:
            return True
        if not self.role:
            return False
        res_perms = self.role.permissions.get(resource, [])
        return action in res_perms or '*' in res_perms

    def __str__(self):
        return self.email
""")

    write_file("apps/accounts/serializers.py", """
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from apps.accounts.models import Role
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
import django.contrib.auth.tokens as tokens
from django.utils.http import urlsafe_base64_decode

User = get_user_model()

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'password_confirm', 'first_name', 'last_name', 'phone')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("A user with this email already exists."))
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": _("Passwords do not match.")})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            if not user:
                raise serializers.ValidationError(_('Unable to log in with provided credentials.'), code='authorization')
            if not user.is_active:
                raise serializers.ValidationError(_('User account is disabled.'), code='authorization')
            attrs['user'] = user
        else:
            raise serializers.ValidationError(_('Must include "email" and "password".'), code='authorization')
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'phone', 'avatar', 'date_joined', 'role')
        read_only_fields = ('id', 'email', 'date_joined', 'role')

class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'role_name', 'is_active', 'date_joined')

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Old password is not correct"))
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": _("New passwords do not match")})
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({"new_password": _("New password must be different from old password")})
        return attrs

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError(_("User with this email does not exist."))

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": _("Passwords do not match")})
        
        try:
            uid = urlsafe_base64_decode(attrs['uid']).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"uid": _("Invalid user id")})
            
        if not tokens.default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError({"token": _("Invalid or expired token")})
            
        attrs['user'] = user
        return attrs
""")

    write_file("apps/accounts/views.py", """
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
    PasswordResetConfirmSerializer
)
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
        
        send_welcome_email.delay(user.id)
        
        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserListSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)

class LoginView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = UserLoginSerializer
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # update last login? optional
        
        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserListSerializer(user).data,
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
        
        send_password_reset_email.delay(user.id, reset_url)
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
""")

    write_file("apps/accounts/permissions.py", """
from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return bool(request.user and (request.user.is_staff or obj.id == request.user.id))

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and (request.user.is_staff or (request.user.role and request.user.role.name == 'admin')))

class HasRolePermission(permissions.BasePermission):
    def __init__(self, resource, action):
        self.resource = resource
        self.action = action

    def has_permission(self, request, view):
        return request.user and request.user.has_perm_for(self.resource, self.action)
""")

    write_file("apps/accounts/signals.py", """
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.accounts.models import Role

User = get_user_model()

@receiver(post_save, sender=User)
def assign_default_role(sender, instance, created, **kwargs):
    if created and not instance.role:
        try:
            default_role = Role.objects.get(is_default=True)
            instance.role = default_role
            instance.save(update_fields=['role'])
        except Role.DoesNotExist:
            pass
""")

    write_file("apps/accounts/tasks.py", """
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
import logging
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger('apps')
User = get_user_model()

@shared_task
def send_welcome_email(user_id):
    try:
        user = User.objects.get(id=user_id)
        send_mail(
            'Welcome to Ezlain',
            f'Hi {user.first_name},\\n\\nWelcome to Ezlain!',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for welcome email")
    except Exception as e:
        logger.error(f"Failed to send welcome email: {e}")

@shared_task
def send_password_reset_email(user_id, reset_url):
    try:
        user = User.objects.get(id=user_id)
        send_mail(
            'Password Reset',
            f'Click here to reset: {reset_url}',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")

@shared_task
def cleanup_inactive_users():
    threshold = timezone.now() - timedelta(days=30)
    users = User.objects.filter(is_active=False, date_joined__lt=threshold)
    count = users.count()
    users.delete()
    logger.info(f"Cleaned up {count} inactive users")
""")

    write_file("apps/accounts/admin.py", """
from django.contrib import admin
from apps.accounts.models import CustomUser, Role

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'role', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('role')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_default', 'description']
""")

    write_file("apps/accounts/urls.py", """
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.accounts.views import (
    RegisterView, LoginView, LogoutView, ChangePasswordView,
    PasswordResetRequestView, PasswordResetConfirmView, UserViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('', include(router.urls)),
]
""")

    write_file("apps/accounts/tests/__init__.py", "")

if __name__ == '__main__':
    run()
