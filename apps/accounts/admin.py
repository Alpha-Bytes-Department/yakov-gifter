from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from apps.accounts.models import CustomUser, Role, ParentChildLink, Referral, CoachingRequest, Feedback

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    model = CustomUser
    list_display = ['email', 'first_name', 'last_name', 'is_pro', 'is_staff', 'is_active', 'role']
    list_filter = ['is_pro', 'is_staff', 'is_active', 'role']
    search_fields = ['email', 'first_name', 'last_name', 'invite_code', 'referral_code']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone', 'avatar', 'bar_mitzvah_date')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'role', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Extra Info', {'fields': ('invite_code', 'referral_code', 'is_pro', 'rc_original_app_user_id')}),
    )

@admin.register(Role)
class RoleAdmin(ModelAdmin):
    list_display = ['name', 'is_default']
    search_fields = ['name']

@admin.register(ParentChildLink)
class ParentChildLinkAdmin(ModelAdmin):
    list_display = ['parent', 'child', 'created_at']
    search_fields = ['parent__email', 'child__email']

@admin.register(Referral)
class ReferralAdmin(ModelAdmin):
    list_display = ['referrer', 'referred_user', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['referrer__email', 'referred_user__email']

@admin.register(CoachingRequest)
class CoachingRequestAdmin(ModelAdmin):
    list_display = ['name', 'email', 'phone', 'coaching_type', 'user', 'created_at']
    list_filter = ['coaching_type', 'created_at']
    search_fields = ['name', 'email', 'phone', 'preferred_times', 'user__email']

@admin.register(Feedback)
class FeedbackAdmin(ModelAdmin):
    list_display = ['user', 'message', 'created_at']
    search_fields = ['user__email', 'message']
