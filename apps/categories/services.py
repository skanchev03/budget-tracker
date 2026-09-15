from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models

from apps.categories.models import Category, Subcategory


def get_categories_for_user(user):
    return (
        Category.objects.filter(
            models.Q(is_default=True) | models.Q(created_by=user)
        )
        .prefetch_related("subcategories")
        .order_by("type", "name")
    )


def get_category_for_user(user, category_id):
    try:
        return Category.objects.get(
            models.Q(is_default=True) | models.Q(created_by=user),
            pk=category_id,
        )
    except Category.DoesNotExist:
        raise PermissionDenied(
            "You do not have access to this category."
        )


def create_category(user, *, name, emoji, category_type):
    name = name.strip()

    if not name:
        raise ValidationError(
            "Category name cannot be empty."
        )

    return Category.objects.create(
        name=name,
        emoji=emoji.strip() or "📁",
        type=category_type,
        is_default=False,
        created_by=user,
    )


def update_category(user, category, *, name, emoji, category_type):
    if category.is_default:
        raise PermissionDenied(
            "Default categories cannot be modified."
        )

    if category.created_by_id != user.id:
        raise PermissionDenied(
            "You cannot modify another user's category."
        )

    category.name = name.strip()
    category.emoji = emoji.strip() or "📁"
    category.type = category_type

    category.full_clean()
    category.save()

    return category


def delete_category(user, category):
    if category.is_default:
        raise PermissionDenied(
            "Default categories cannot be deleted."
        )

    if category.created_by_id != user.id:
        raise PermissionDenied(
            "You cannot delete another user's category."
        )

    category.delete()


def get_subcategories_for_user(user):
    return (
        Subcategory.objects.filter(
            models.Q(is_default=True)
            | models.Q(created_by=user)
        )
        .select_related("category")
        .order_by("category__type", "category__name", "name")
    )


def get_subcategory_for_user(user, subcategory_id):
    try:
        return Subcategory.objects.get(
            models.Q(is_default=True)
            | models.Q(created_by=user),
            pk=subcategory_id,
        )
    except Subcategory.DoesNotExist:
        raise PermissionDenied(
            "You do not have access to this subcategory."
        )


def create_subcategory(user, *, category, name):
    name = name.strip()

    if not name:
        raise ValidationError(
            "Subcategory name cannot be empty."
        )

    if (
        not category.is_default
        and category.created_by_id != user.id
    ):
        raise PermissionDenied(
            "You cannot use another user's category."
        )

    return Subcategory.objects.create(
        category=category,
        name=name,
        is_default=False,
        created_by=user,
    )


def update_subcategory(user, subcategory, *, category, name):
    if subcategory.is_default:
        raise PermissionDenied(
            "Default subcategories cannot be modified."
        )

    if subcategory.created_by_id != user.id:
        raise PermissionDenied(
            "You cannot modify another user's subcategory."
        )

    if (
        not category.is_default
        and category.created_by_id != user.id
    ):
        raise PermissionDenied(
            "You cannot move a subcategory to another user's category."
        )

    subcategory.category = category
    subcategory.name = name.strip()

    subcategory.full_clean()
    subcategory.save()

    return subcategory


def delete_subcategory(user, subcategory):
    if subcategory.is_default:
        raise PermissionDenied(
            "Default subcategories cannot be deleted."
        )

    if subcategory.created_by_id != user.id:
        raise PermissionDenied(
            "You cannot delete another user's subcategory."
        )

    subcategory.delete()