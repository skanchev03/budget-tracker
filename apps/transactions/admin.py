from django.contrib import admin

from apps.transactions.models import Transaction, Transfer


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "type",
        "amount",
        "currency",
        "account",
        "category",
        "subcategory",
        "occurred_at",
    )

    list_filter = (
        "type",
        "currency",
        "category",
    )

    search_fields = (
        "user__username",
        "user__email",
        "person",
        "description",
        "account__name",
        "category__name",
        "subcategory__name",
    )

    ordering = (
        "-occurred_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "from_account",
        "to_account",
        "amount_from",
        "from_currency",
        "amount_to",
        "to_currency",
        "exchange_rate",
        "occurred_at",
    )

    list_filter = (
        "from_currency",
        "to_currency",
    )

    search_fields = (
        "user__username",
        "user__email",
        "from_account__name",
        "to_account__name",
        "description",
    )

    ordering = (
        "-occurred_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )