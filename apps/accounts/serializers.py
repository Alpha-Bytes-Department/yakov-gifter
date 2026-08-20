from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from apps.accounts.models import Role, CoachingRequest, Feedback
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
import django.contrib.auth.tokens as tokens
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

User = get_user_model()

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    invite_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    referral_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    is_parent = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = User
        fields = ('email', 'password', 'password_confirm', 'first_name', 'last_name', 'full_name', 'phone', 'invite_code', 'referral_code', 'is_parent', 'date_of_birth')
        extra_kwargs = {
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True}
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("A user with this email already exists."))
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": _("Passwords do not match.")})
        
        # Handle full_name splitting if first_name/last_name not provided
        full_name = attrs.get('full_name')
        if full_name and not attrs.get('first_name') and not attrs.get('last_name'):
            parts = full_name.strip().split(' ')
            if len(parts) > 1:
                attrs['first_name'] = ' '.join(parts[:-1])
                attrs['last_name'] = parts[-1]
            else:
                attrs['first_name'] = parts[0]
                attrs['last_name'] = ''

        # Ensure we have at least first_name (defaulting if still empty)
        if not attrs.get('first_name'):
            attrs['first_name'] = 'User'
        if not attrs.get('last_name'):
            attrs['last_name'] = ''
        
        is_parent = attrs.get('is_parent', False)
        invite_code = attrs.get('invite_code')
        referral_code = attrs.get('referral_code')

        if is_parent:
            if not invite_code or not str(invite_code).strip():
                raise serializers.ValidationError({"invite_code": _("An invite code is required to create a parent account.")})
            try:
                child = User.objects.get(invite_code=str(invite_code).strip())
                attrs['child_user'] = child
            except User.DoesNotExist:
                raise serializers.ValidationError({"invite_code": _("Invalid invite code. Please check with your son.")})
        elif invite_code:
            try:
                child = User.objects.get(invite_code=str(invite_code).strip())
                attrs['child_user'] = child
            except User.DoesNotExist:
                raise serializers.ValidationError({"invite_code": _("Invalid invite code.")})

        if referral_code and str(referral_code).strip():
            referrer = User.objects.filter(referral_code=str(referral_code).strip()).first()
            if referrer:
                attrs['referrer_user'] = referrer
                
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        child_user = validated_data.pop('child_user', None)
        referrer_user = validated_data.pop('referrer_user', None)
        invite_code = validated_data.pop('invite_code', None)
        referral_code = validated_data.pop('referral_code', None)
        full_name = validated_data.pop('full_name', None)
        is_parent = validated_data.pop('is_parent', False)
        
        user = User.objects.create_user(**validated_data)
        
        # If invite_code is provided OR is_parent is True, assign Parent role
        if child_user or is_parent:
            from apps.accounts.models import ParentChildLink, Role
            parent_role, _ = Role.objects.get_or_create(name='Parent')
            user.role = parent_role
            user.save(update_fields=['role'])
            
            if child_user:
                ParentChildLink.objects.get_or_create(parent=user, child=child_user)

        if referrer_user:
            from apps.accounts.models import Referral
            Referral.objects.get_or_create(referrer=referrer_user, referred_user=user, defaults={'status': 'invited'})
            
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        raw_email = attrs.get('email', '')
        email = raw_email.strip().lower() if raw_email else ''
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            if not user:
                try:
                    user_obj = User.objects.get(email__iexact=email)
                    if user_obj.check_password(password):
                        user = user_obj
                except User.DoesNotExist:
                    user = None

            if not user:
                raise serializers.ValidationError(_('Unable to log in with provided credentials.'), code='authorization')
            if not user.is_active:
                raise serializers.ValidationError(_('User account is disabled.'), code='authorization')
            attrs['user'] = user
        else:
            raise serializers.ValidationError(_('Must include "email" and "password".'), code='authorization')
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    role = serializers.SerializerMethodField()
    bar_mitzvah_date = serializers.SerializerMethodField()
    linked_children = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'avatar', 'date_joined', 'role', 'is_pro',
            'bar_mitzvah_date', 'date_of_birth', 'invite_code', 'linked_children'
        )
        read_only_fields = ('id', 'email', 'date_joined', 'role', 'invite_code', 'is_pro', 'linked_children')
        extra_kwargs = {
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True}
        }

    def get_role(self, obj):
        if obj.role:
            return obj.role.name
        return "Student"

    def get_bar_mitzvah_date(self, obj):
        if obj.bar_mitzvah_date:
            return obj.bar_mitzvah_date.isoformat()
        
        if obj.date_of_birth:
            try:
                from pyluach import dates
                import datetime
                heb_dob = dates.GregorianDate.frompydate(obj.date_of_birth).to_heb()
                heb_bm = dates.HebrewDate(heb_dob.year + 13, heb_dob.month, heb_dob.day)
                return heb_bm.to_pydate().isoformat()
            except Exception:
                try:
                    return obj.date_of_birth.replace(year=obj.date_of_birth.year + 13).isoformat()
                except ValueError:
                    import datetime
                    return (obj.date_of_birth + datetime.timedelta(days=365*13 + 3)).isoformat()
        return None

    def get_linked_children(self, obj):
        from apps.accounts.models import ParentChildLink
        links = ParentChildLink.objects.filter(parent=obj).select_related('child')
        return [
            {
                'id': link.child.id,
                'full_name': link.child.full_name,
                'email': link.child.email,
                'invite_code': link.child.invite_code,
            }
            for link in links
        ]

    def update(self, instance, validated_data):
        full_name = self.initial_data.get('full_name')
        if full_name and 'first_name' not in validated_data and 'last_name' not in validated_data:
            parts = full_name.strip().split(' ')
            if len(parts) > 1:
                validated_data['first_name'] = ' '.join(parts[:-1])
                validated_data['last_name'] = parts[-1]
            else:
                validated_data['first_name'] = parts[0]
                validated_data['last_name'] = ''
        return super().update(instance, validated_data)

class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'role_name', 'is_active', 'date_joined')

class AdminUserListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    parents = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'full_name', 'is_pro', 'date_joined',
            'rc_entitlement_id', 'rc_subscription_status', 'rc_expires_date',
            'parents', 'children', 'profile'
        )

    def get_parents(self, obj):
        return [
            {'id': link.parent.id, 'full_name': link.parent.full_name, 'email': link.parent.email}
            for link in obj.parent_links.all()
        ]
        
    def get_children(self, obj):
        return [
            {'id': link.child.id, 'full_name': link.child.full_name, 'email': link.child.email}
            for link in obj.children_links.all()
        ]

    def get_profile(self, obj):
        try:
            from apps.users_and_subs.models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=obj)
            return {
                'subscription_type': profile.subscription_type,
                'has_one_time_purchase_36': profile.has_one_time_purchase_36,
                'date_of_birth': profile.date_of_birth.isoformat() if profile.date_of_birth else None,
                'weeks_until_bar_mitzvah': profile.weeks_until_bar_mitzvah,
                'stripe_customer_id': profile.stripe_customer_id,
                'referral_count': profile.referral_count,
                'referred_by_email': profile.referred_by.user.email if profile.referred_by and profile.referred_by.user else None
            }
        except Exception as e:
            return {
                'subscription_type': 'Free',
                'has_one_time_purchase_36': False,
                'date_of_birth': None,
                'weeks_until_bar_mitzvah': None,
                'stripe_customer_id': '',
                'referral_count': 0,
                'referred_by_email': None
            }

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

class LinkChildSerializer(serializers.Serializer):
    invite_code = serializers.CharField(required=True)

    def validate_invite_code(self, value):
        try:
            child = User.objects.get(invite_code=value)
            return child
        except User.DoesNotExist:
            raise serializers.ValidationError(_("Invalid invite code."))

class CoachingRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoachingRequest
        fields = ('id', 'name', 'phone', 'email', 'preferred_times', 'coaching_type', 'created_at')
        read_only_fields = ('id', 'created_at')
        extra_kwargs = {
            'phone': {'required': False, 'allow_blank': True},
            'name': {'required': False, 'allow_blank': True},
            'email': {'required': False, 'allow_blank': True},
            'preferred_times': {'required': False, 'allow_blank': True},
        }

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ('id', 'message', 'created_at')
        read_only_fields = ('id', 'created_at')
