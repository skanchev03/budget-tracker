from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.core.models import Currency, ExchangeRate


class CurrencyModelTests(TestCase):
    def setUp(self):
        self.eur = Currency.objects.get(code="EUR")

    def test_currency_str(self):
        self.assertEqual(
            str(self.eur),
            "EUR - Euro",
        )

    def test_currency_code_is_unique(self):
        with self.assertRaises(IntegrityError):
            Currency.objects.create(
                code="EUR",
                name="Another Euro",
                symbol="€",
            )

    def test_currency_fields_are_saved_correctly(self):
        self.assertEqual(self.eur.code, "EUR")
        self.assertEqual(self.eur.name, "Euro")
        self.assertEqual(self.eur.symbol, "€")


class ExchangeRateModelTests(TestCase):
    def setUp(self):
        self.eur = Currency.objects.get(code="EUR")
        self.usd = Currency.objects.get(code="USD")

    def test_exchange_rate_str(self):
        exchange_rate = ExchangeRate.objects.create(
            from_currency=self.eur,
            to_currency=self.usd,
            rate=Decimal("1.1700000000"),
            valid_at=timezone.now(),
        )

        self.assertEqual(
            str(exchange_rate),
            "EUR → USD: 1.1700000000",
        )

    def test_exchange_rate_can_be_created_with_different_currencies(self):
        exchange_rate = ExchangeRate.objects.create(
            from_currency=self.eur,
            to_currency=self.usd,
            rate=Decimal("1.1700000000"),
            valid_at=timezone.now(),
        )

        self.assertEqual(exchange_rate.from_currency, self.eur)
        self.assertEqual(exchange_rate.to_currency, self.usd)
        self.assertEqual(exchange_rate.rate, Decimal("1.1700000000"))

    def test_same_currency_is_invalid(self):
        exchange_rate = ExchangeRate(
            from_currency=self.eur,
            to_currency=self.eur,
            rate=Decimal("1.0000000000"),
            valid_at=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            exchange_rate.full_clean()

    def test_zero_exchange_rate_is_invalid(self):
        exchange_rate = ExchangeRate(
            from_currency=self.eur,
            to_currency=self.usd,
            rate=Decimal("0"),
            valid_at=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            exchange_rate.full_clean()

    def test_negative_exchange_rate_is_invalid(self):
        exchange_rate = ExchangeRate(
            from_currency=self.eur,
            to_currency=self.usd,
            rate=Decimal("-1.0000000000"),
            valid_at=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            exchange_rate.full_clean()

    def test_duplicate_exchange_rate_at_same_time_is_not_allowed(self):
        valid_at = timezone.now()

        ExchangeRate.objects.create(
            from_currency=self.eur,
            to_currency=self.usd,
            rate=Decimal("1.1700000000"),
            valid_at=valid_at,
        )

        with self.assertRaises(IntegrityError):
            ExchangeRate.objects.create(
                from_currency=self.eur,
                to_currency=self.usd,
                rate=Decimal("1.1800000000"),
                valid_at=valid_at,
            )

    def test_same_currency_pair_can_have_rates_at_different_times(self):
        first_time = timezone.now()
        second_time = first_time + timedelta(hours=1)

        first_rate = ExchangeRate.objects.create(
            from_currency=self.eur,
            to_currency=self.usd,
            rate=Decimal("1.1700000000"),
            valid_at=first_time,
        )

        second_rate = ExchangeRate.objects.create(
            from_currency=self.eur,
            to_currency=self.usd,
            rate=Decimal("1.1800000000"),
            valid_at=second_time,
        )

        self.assertNotEqual(first_rate.valid_at, second_rate.valid_at)
        self.assertEqual(ExchangeRate.objects.count(), 2)

    def test_source_is_optional(self):
        exchange_rate = ExchangeRate.objects.create(
            from_currency=self.eur,
            to_currency=self.usd,
            rate=Decimal("1.1700000000"),
            valid_at=timezone.now(),
        )

        self.assertIsNone(exchange_rate.source)

    def test_source_is_saved(self):
        exchange_rate = ExchangeRate.objects.create(
            from_currency=self.eur,
            to_currency=self.usd,
            rate=Decimal("1.1700000000"),
            valid_at=timezone.now(),
            source="ECB",
        )

        self.assertEqual(exchange_rate.source, "ECB")