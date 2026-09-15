from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.users.emails import (
    send_two_factor_email,
    send_verification_email,
)
from apps.users.forms import (
    LoginForm,
    RegistrationForm,
    TwoFactorForm,
    ProfileForm,
    UserSettingsForm,
)
from apps.users.services import (
    create_two_factor_code,
    login_user,
    register_user,
    verify_email_token,
    verify_two_factor_code,
    update_profile,
    update_user_settings,
)


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard:dashboard")
        
    if request.method == "POST":
        form = RegistrationForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            user, raw_token = register_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                date_of_birth=form.cleaned_data.get(
                    "date_of_birth"
                ),
                country=form.cleaned_data["country"],
                profile_picture=form.cleaned_data.get(
                    "profile_picture"
                ),
            )

            send_verification_email(
                user,
                raw_token,
            )

            return redirect(
                "registration-success"
            )

    else:
        form = RegistrationForm()

    return render(
        request,
        "users/register.html",
        {"form": form},
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:dashboard")
        
    if request.method == "POST":
        form = LoginForm(request.POST)

        if form.is_valid():
            user = login_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )

            if user is None:
                form.add_error(
                    None,
                    "Invalid username or password, "
                    "or email is not verified.",
                )
            else:
                if user.two_fa_enabled:
                    raw_code = create_two_factor_code(
                        user
                    )

                    send_two_factor_email(
                        user,
                        raw_code,
                    )

                    request.session[
                        "pending_2fa_user_id"
                    ] = user.pk

                    return redirect(
                        "verify-2fa"
                    )

                login(
                    request,
                    user,
                )

                return redirect(
                    "dashboard:dashboard"
                )

    else:
        form = LoginForm()

    return render(
        request,
        "users/login.html",
        {"form": form},
    )


def verify_two_factor(request):
    pending_user_id = request.session.get(
        "pending_2fa_user_id"
    )

    if pending_user_id is None:
        return redirect("login")

    User = get_user_model()

    try:
        user = User.objects.get(
            pk=pending_user_id
        )
    except User.DoesNotExist:
        request.session.pop(
            "pending_2fa_user_id",
            None,
        )
        return redirect("login")

    if request.method == "POST":
        form = TwoFactorForm(request.POST)

        if form.is_valid():
            is_valid = verify_two_factor_code(
                user,
                form.cleaned_data["code"],
            )

            if is_valid:
                request.session.pop(
                    "pending_2fa_user_id",
                    None,
                )

                login(
                    request,
                    user,
                )

                return redirect(
                    "dashboard:dashboard"
                )

            form.add_error(
                "code",
                "Invalid or expired verification code.",
            )
    else:
        form = TwoFactorForm()

    return render(
        request,
        "users/verify_2fa.html",
        {"form": form},
    )


def registration_success(request):
    return render(
        request,
        "users/registration_success.html",
    )


def verify_email(request, token):
    is_verified = verify_email_token(
        token
    )

    if is_verified:
        return render(
            request,
            "users/email_verified.html",
        )

    return render(
        request,
        "users/email_verification_failed.html",
        status=400,
    )


@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("login")

    return redirect("dashboard:dashboard")


@login_required
def profile(request):
    user = request.user
    user_profile = user.profile

    profile_form = ProfileForm(
        instance=user_profile,
    )

    settings_form = UserSettingsForm(
        instance=user,
    )

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "profile":
            profile_form = ProfileForm(
                request.POST,
                request.FILES,
                instance=user_profile,
            )

            if profile_form.is_valid():
                update_profile(
                    user,
                    profile_picture=profile_form.cleaned_data.get(
                        "profile_picture"
                    ),
                    date_of_birth=profile_form.cleaned_data.get(
                        "date_of_birth"
                    ),
                    country=profile_form.cleaned_data.get(
                        "country"
                    ),
                )

                return redirect("profile")

        elif form_type == "settings":
            settings_form = UserSettingsForm(
                request.POST,
                instance=user,
            )

            if settings_form.is_valid():
                update_user_settings(
                    user,
                    base_currency=settings_form.cleaned_data[
                        "base_currency"
                    ],
                    language=settings_form.cleaned_data[
                        "language"
                    ],
                    two_fa_enabled=settings_form.cleaned_data[
                        "two_fa_enabled"
                    ],
                )

                return redirect("profile")

    return render(
        request,
        "users/profile.html",
        {
            "profile_form": profile_form,
            "settings_form": settings_form,
        },
    )