from django.db import models

from apps.core.models import Currency
from apps.users.models import User


class Account(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="accounts",
    )

    name = models.CharField(
        max_length=100,
    )

    emoji = models.CharField(
        max_length=10,
        default="💰",
    )

    color = models.CharField(
        max_length=7,
        default="#3498DB",
    )

    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="accounts",
    )

    opening_balance = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=0,
    )

    current_balance = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=0,
    )

    display_order = models.IntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["display_order", "name"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    color__regex=r"^#[0-9A-Fa-f]{6}$"
                ),
                name="account_color_valid_hex",
            ),
        ]

    def __str__(self):
        return f"{self.emoji} {self.name}"