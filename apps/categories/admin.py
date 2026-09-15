from django.contrib import admin

from apps.categories.models import Category, Subcategory


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "emoji",
        "type",
        "is_default",
        "created_by",
        "created_at",
    )

    list_filter = (
        "type",
        "is_default",
    )

    search_fields = (
        "name",
        "created_by__username",
        "created_by__email",
    )

    ordering = (
        "type",
        "name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "is_default",
        "created_by",
        "created_at",
    )

    list_filter = (
        "is_default",
        "category",
    )

    search_fields = (
        "name",
        "category__name",
        "created_by__username",
        "created_by__email",
    )

    ordering = (
        "category__type",
        "category__name",
        "name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )