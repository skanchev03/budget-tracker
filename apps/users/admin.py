from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.users.models import (
    EmailVerificationToken,
    Profile,
    TwoFactorCode,
    User,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "base_currency",
        "language",
        "is_email_verified",
        "two_fa_enabled",
        "is_active",
    )
    list_filter = (
        "language",
        "is_email_verified",
        "two_fa_enabled",
        "is_active",
        "is_staff",
    )
    search_fields = ("username", "email")

    fieldsets = UserAdmin.fieldsets + (
        (
            "Budget Tracker",
            {
                "fields": (
                    "base_currency",
                    "language",
                    "is_email_verified",
                    "two_fa_enabled",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    readonly_fields = ("created_at", "updated_at")

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Budget Tracker",
            {
                "fields": (
                    "email",
                    "base_currency",
                    "language",
                    "is_email_verified",
                    "two_fa_enabled",
                )
            },
        ),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "country",
        "date_of_birth",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "country",
    )
    list_filter = ("country",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "expires_at",
        "used_at",
        "created_at",
    )
    search_fields = (
        "user__username",
        "user__email",
    )
    list_filter = ("used_at",)
    readonly_fields = ("created_at",)
    exclude = ("token_hash",)


@admin.register(TwoFactorCode)
class TwoFactorCodeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "expires_at",
        "used_at",
        "attempts",
        "created_at",
    )
    search_fields = (
        "user__username",
        "user__email",
    )
    list_filter = ("used_at",)
    readonly_fields = ("created_at",)
    exclude = ("code_hash",)