from django.contrib import admin

from apps.core.models import Currency, ExchangeRate


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "symbol")
    search_fields = ("code", "name")
    ordering = ("code",)


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = (
        "from_currency",
        "to_currency",
        "rate",
        "valid_at",
        "source",
    )
    list_filter = ("from_currency", "to_currency")
    search_fields = (
        "from_currency__code",
        "to_currency__code",
        "source",
    )
    ordering = ("-valid_at",)