from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import Currency


class User(AbstractUser):
    email = models.EmailField(unique=True)

    base_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="users",
    )

    language = models.CharField(
        max_length=5,
        choices=[
            ("bg", "Bulgarian"),
            ("en", "English"),
        ],
        default="bg",
    )

    is_email_verified = models.BooleanField(default=False)
    two_fa_enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        null=True,
        blank=True,
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True,
    )

    country = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user.username}"


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )

    token_hash = models.CharField(
        max_length=128,
    )

    expires_at = models.DateTimeField()

    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"Email verification token: {self.user.username}"


class TwoFactorCode(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="two_factor_codes",
    )

    code_hash = models.CharField(
        max_length=128,
    )

    expires_at = models.DateTimeField()

    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    attempts = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"2FA code: {self.user.username}"