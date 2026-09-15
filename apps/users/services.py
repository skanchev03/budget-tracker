import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from apps.core.models import Currency
from apps.users.models import (
    EmailVerificationToken,
    Profile,
    TwoFactorCode,
    User,
)


def register_user(
    *,
    username,
    email,
    password,
    date_of_birth=None,
    country,
    profile_picture=None,
):
    """
    Creates a new user, their profile, and an email verification token.
    """

    eur = Currency.objects.get(code="EUR")

    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            base_currency=eur,
            language="bg",
            is_email_verified=False,
            two_fa_enabled=True,
        )

        Profile.objects.create(
            user=user,
            date_of_birth=date_of_birth,
            country=country,
            profile_picture=profile_picture,
        )

        raw_token = create_email_verification_token(user)

    return user, raw_token


def create_email_verification_token(user):
    """
    Creates a secure email verification token and stores only its hash.
    """

    raw_token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    expires_at = timezone.now() + timedelta(hours=24)

    EmailVerificationToken.objects.create(
        user=user,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    return raw_token


def verify_email_token(raw_token):
    """
    Verifies an email verification token and marks the user's email
    as verified.
    """

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    with transaction.atomic():
        verification_token = (
            EmailVerificationToken.objects
            .select_for_update()
            .select_related("user")
            .filter(
                token_hash=token_hash,
                used_at__isnull=True,
            )
            .first()
        )

        if verification_token is None:
            return False

        if verification_token.expires_at <= timezone.now():
            return False

        user = verification_token.user

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified", "updated_at"])

        verification_token.used_at = timezone.now()
        verification_token.save(update_fields=["used_at"])

    return True


def create_two_factor_code(user):
    """
    Creates a secure 6-digit 2FA code and stores only its hash.
    The code is valid for 10 minutes.
    """

    raw_code = f"{secrets.randbelow(1_000_000):06d}"

    code_hash = make_password(raw_code)

    expires_at = timezone.now() + timedelta(minutes=10)

    TwoFactorCode.objects.create(
        user=user,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    return raw_code


def verify_two_factor_code(user, raw_code):
    """
    Verifies the latest unused 2FA code for the user.
    Returns True when the code is valid.
    """

    with transaction.atomic():
        two_factor_code = (
            TwoFactorCode.objects
            .select_for_update()
            .filter(
                user=user,
                used_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )

        if two_factor_code is None:
            return False

        if two_factor_code.expires_at <= timezone.now():
            return False

        if two_factor_code.attempts >= 5:
            return False

        if not check_password(
            raw_code,
            two_factor_code.code_hash,
        ):
            two_factor_code.attempts += 1
            two_factor_code.save(
                update_fields=["attempts"]
            )
            return False

        two_factor_code.used_at = timezone.now()
        two_factor_code.save(
            update_fields=["used_at"]
        )

    return True


def login_user(*, username, password):
    """
    Authenticates a user using username and password.

    Returns the authenticated user when the credentials are valid
    and the email has been verified.

    Returns None when authentication fails.
    """

    user = authenticate(
        username=username,
        password=password,
    )

    if user is None:
        return None

    if not user.is_active:
        return None

    if not user.is_email_verified:
        return None

    return user


@transaction.atomic
def update_profile(
    user: User,
    *,
    profile_picture=None,
    date_of_birth=None,
    country=None,
) -> Profile:
    profile, _ = Profile.objects.select_for_update().get_or_create(
        user=user,
        defaults={
            "country": country or "",
        },
    )

    if profile_picture is False:
        profile.profile_picture = None
    elif profile_picture is not None:
        profile.profile_picture = profile_picture

    if date_of_birth is not None:
        profile.date_of_birth = date_of_birth

    if country is not None:
        profile.country = country.strip()

    profile.save()

    return profile


@transaction.atomic
def update_user_settings(
    user: User,
    *,
    base_currency,
    language: str,
    two_fa_enabled: bool,
) -> User:
    user = User.objects.select_for_update().get(pk=user.pk)

    user.base_currency = base_currency
    user.language = language
    user.two_fa_enabled = two_fa_enabled

    user.save(
        update_fields=[
            "base_currency",
            "language",
            "two_fa_enabled",
            "updated_at",
        ]
    )

    return user