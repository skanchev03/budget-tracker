from django.contrib import admin

from apps.accounts.models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "currency",
        "opening_balance",
        "current_balance",
        "display_order",
        "is_active",
        "created_at",
    )

    list_filter = (
        "currency",
        "is_active",
    )

    search_fields = (
        "name",
        "user__username",
        "user__email",
    )

    ordering = (
        "user",
        "display_order",
        "name",
    )

    readonly_fields = (
        "current_balance",
        "created_at",
        "updated_at",
    )