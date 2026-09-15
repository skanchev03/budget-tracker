from django.db import models
from django.core.validators import MinValueValidator


class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=5)

    def __str__(self):
        return f"{self.code} - {self.name}"


class ExchangeRate(models.Model):
    from_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="exchange_rates_from",
    )

    to_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="exchange_rates_to",
    )

    rate = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        validators=[
            MinValueValidator(0.0000000001),
        ],
    )

    valid_at = models.DateTimeField()

    source = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "from_currency",
                    "to_currency",
                    "valid_at",
                ],
                name="unique_exchange_rate_at_time",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "from_currency",
                    "to_currency",
                    "valid_at",
                ],
                name="exchange_rate_lookup_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.from_currency.code} → "
            f"{self.to_currency.code}: {self.rate}"
        )

    def clean(self):
        super().clean()

        from django.core.exceptions import ValidationError

        if (
            self.from_currency_id
            and self.to_currency_id
            and self.from_currency_id == self.to_currency_id
        ):
            raise ValidationError(
                {
                    "to_currency": (
                        "The source and destination currencies must be different."
                    )
                }
            )