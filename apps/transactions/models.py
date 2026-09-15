from django.core.validators import MinValueValidator
from django.db import models

from apps.accounts.models import Account
from apps.categories.models import Category, Subcategory
from apps.core.models import Currency
from apps.users.models import User


class Transaction(models.Model):
    EXPENSE = "EXPENSE"
    INCOME = "INCOME"

    TYPE_CHOICES = [
        (EXPENSE, "Expense"),
        (INCOME, "Income"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    amount = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        validators=[
            MinValueValidator(0.0001),
        ],
    )

    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    occurred_at = models.DateTimeField()

    person = models.CharField(
        max_length=150,
        null=True,
        blank=True,
    )

    description = models.TextField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.type}: {self.amount} {self.currency.code}"

    def clean(self):
        super().clean()

        if self.account_id and self.user_id:
            if self.account.user_id != self.user_id:
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    {"account": "The account must belong to the transaction user."}
                )

        if self.category_id and self.type:
            if self.category.type != self.type:
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    {"category": "The category type must match the transaction type."}
                )

        if self.subcategory_id and self.category_id:
            if self.subcategory.category_id != self.category_id:
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    {
                        "subcategory": (
                            "The subcategory must belong to the selected category."
                        )
                    }
                )

        if self.account_id and self.currency_id:
            if self.account.currency_id != self.currency_id:
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    {"currency": "The transaction currency must match the account currency."}
                )

        if self.category_id and self.user_id:
            if not self.category.is_default and self.category.created_by_id != self.user_id:
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    {"category": "You can only use your own custom categories."}
                )

        if self.subcategory_id and self.user_id:
            if (
                not self.subcategory.is_default
                and self.subcategory.created_by_id != self.user_id
            ):
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    {"subcategory": "You can only use your own custom subcategories."}
                )


class Transfer(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="transfers",
    )

    from_account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="outgoing_transfers",
    )

    to_account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="incoming_transfers",
    )

    amount_from = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        validators=[
            MinValueValidator(0.0001),
        ],
    )

    amount_to = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        validators=[
            MinValueValidator(0.0001),
        ],
    )

    from_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
    )

    to_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
    )

    exchange_rate = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        validators=[
            MinValueValidator(0.0000000001),
        ],
    )

    occurred_at = models.DateTimeField()

    description = models.TextField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"Transfer: {self.amount_from} {self.from_currency.code} "
            f"→ {self.amount_to} {self.to_currency.code}"
        )

    def clean(self):
        super().clean()

        from django.core.exceptions import ValidationError

        if self.from_account_id and self.to_account_id:
            if self.from_account_id == self.to_account_id:
                raise ValidationError(
                    {
                        "to_account": (
                            "The source and destination accounts must be different."
                        )
                    }
                )

        if self.from_account_id and self.user_id:
            if self.from_account.user_id != self.user_id:
                raise ValidationError(
                    {
                        "from_account": (
                            "The source account must belong to the transfer user."
                        )
                    }
                )

        if self.to_account_id and self.user_id:
            if self.to_account.user_id != self.user_id:
                raise ValidationError(
                    {
                        "to_account": (
                            "The destination account must belong to the transfer user."
                        )
                    }
                )

        if self.from_account_id and self.from_currency_id:
            if self.from_account.currency_id != self.from_currency_id:
                raise ValidationError(
                    {
                        "from_currency": (
                            "The source currency must match the source account currency."
                        )
                    }
                )

        if self.to_account_id and self.to_currency_id:
            if self.to_account.currency_id != self.to_currency_id:
                raise ValidationError(
                    {
                        "to_currency": (
                            "The destination currency must match the destination account currency."
                        )
                    }
                )

        if (
            self.from_currency_id
            and self.to_currency_id
            and self.exchange_rate
            and self.amount_from
            and self.amount_to
        ):
            expected_amount_to = self.amount_from * self.exchange_rate

            if abs(expected_amount_to - self.amount_to) > 0.0001:
                raise ValidationError(
                    {
                        "amount_to": (
                            "The destination amount does not match "
                            "the source amount and exchange rate."
                        )
                    }
                )