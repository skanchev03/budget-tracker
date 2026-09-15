from django.urls import path

from apps.users.views import (
    login_view,
    logout_view,
    register,
    registration_success,
    verify_email,
    verify_two_factor,
    profile,
)


urlpatterns = [
    path(
        "login/",
        login_view,
        name="login",
    ),
    path(
        "logout/",
        logout_view,
        name="logout",
    ),
    path(
        "register/",
        register,
        name="register",
    ),
    path(
        "registration-success/",
        registration_success,
        name="registration-success",
    ),
    path(
        "verify-email/<str:token>/",
        verify_email,
        name="verify-email",
    ),
    path(
        "2fa/",
        verify_two_factor,
        name="verify-2fa",
    ),
    path(
        "profile/",
        profile,
        name="profile"
    ),
]