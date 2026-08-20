from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.accounts.views import (
    RegisterView, LoginView, LogoutView, ChangePasswordView,
    PasswordResetRequestView, PasswordResetConfirmView, UserViewSet,
    LinkChildView
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
    path('link-child/', LinkChildView.as_view(), name='link_child'),
    path('', include(router.urls)),
]
