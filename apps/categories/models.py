from django.db import models

from apps.users.models import User


class Category(models.Model):
    EXPENSE = "EXPENSE"
    INCOME = "INCOME"

    TYPE_CHOICES = [
        (EXPENSE, "Expense"),
        (INCOME, "Income"),
    ]

    name = models.CharField(max_length=100)

    emoji = models.CharField(
        max_length=10,
        default="📁",
    )

    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
    )

    is_default = models.BooleanField(
        default=False,
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="custom_categories",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.emoji} {self.name}"


class Subcategory(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="subcategories",
    )

    name = models.CharField(max_length=100)

    is_default = models.BooleanField(
        default=False,
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="custom_subcategories",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.category.name} → {self.name}"