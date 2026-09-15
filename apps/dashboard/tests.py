from decimal import Decimal
from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account
from apps.categories.models import Category, Subcategory
from apps.core.models import Currency, ExchangeRate
from apps.dashboard.services import (
    convert_amount,
    get_dashboard_summary,
    get_expenses_by_category,
    get_exchange_rate,
    get_recent_transactions,
    get_recent_transfers,
    get_total_balance,
    get_monthly_income_expenses,
)
from apps.transactions.services import (
    create_expense,
    create_income,
    create_transfer,
)
from apps.transactions.models import Transaction, Transfer
from apps.users.models import User, Profile


class DashboardServiceTests(TestCase):

    def setUp(self):
        # ---------------------------------------------------------
        # Existing seeded currency
        # ---------------------------------------------------------

        self.eur = Currency.objects.get(
            code="EUR",
        )

        # ---------------------------------------------------------
        # User
        # ---------------------------------------------------------

        self.user = User.objects.create_user(
            username="dashboard_user",
            email="dashboard@example.com",
            password="StrongPassword123!",
            base_currency=self.eur,
            language="en",
            is_email_verified=True,
            two_fa_enabled=True,
        )

        Profile.objects.create(
            user=self.user,
            country="Bulgaria",
        )

        # ---------------------------------------------------------
        # Accounts
        # ---------------------------------------------------------

        self.cash = Account.objects.create(
            user=self.user,
            name="Cash",
            emoji="💵",
            color="#3498DB",
            currency=self.eur,
            opening_balance=500,
            current_balance=500,
        )

        self.revolut = Account.objects.create(
            user=self.user,
            name="Revolut",
            emoji="💳",
            color="#9B59B6",
            currency=self.eur,
            opening_balance=200,
            current_balance=200,
        )

        # ---------------------------------------------------------
        # Existing seeded default categories
        # ---------------------------------------------------------

        self.food = Category.objects.get(
            name="Food & Drinks",
            type=Category.EXPENSE,
            is_default=True,
        )

        self.shopping = Category.objects.get(
            name="Shopping",
            type=Category.EXPENSE,
            is_default=True,
        )

        self.income_category = Category.objects.get(
            name="Income",
            type=Category.INCOME,
            is_default=True,
        )

        # ---------------------------------------------------------
        # Existing seeded default subcategories
        # ---------------------------------------------------------

        self.groceries = Subcategory.objects.get(
            category=self.food,
            name="Groceries",
            is_default=True,
        )

        self.clothes = Subcategory.objects.get(
            category=self.shopping,
            name="Clothes",
            is_default=True,
        )

        self.wage = Subcategory.objects.get(
            category=self.income_category,
            name="Wage",
            is_default=True,
        )

        # ---------------------------------------------------------
        # Transactions
        # ---------------------------------------------------------

        self.expense = Transaction.objects.create(
            user=self.user,
            account=self.cash,
            type=Transaction.EXPENSE,
            category=self.food,
            subcategory=self.groceries,
            amount=Decimal("50.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
        )

        self.second_expense = Transaction.objects.create(
            user=self.user,
            account=self.cash,
            type=Transaction.EXPENSE,
            category=self.shopping,
            subcategory=self.clothes,
            amount=Decimal("100.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
        )

        self.income = Transaction.objects.create(
            user=self.user,
            account=self.cash,
            type=Transaction.INCOME,
            category=self.income_category,
            subcategory=self.wage,
            amount=Decimal("500.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
        )

    # =============================================================
    # Dashboard summary
    # =============================================================

    def test_dashboard_summary(self):

        summary = get_dashboard_summary(
            self.user,
        )

        self.assertEqual(
            summary["account_count"],
            2,
        )

        self.assertEqual(
            summary["income"],
            Decimal("500.00"),
        )

        self.assertEqual(
            summary["expenses"],
            Decimal("150.00"),
        )

        self.assertEqual(
            summary["net_cash_flow"],
            Decimal("350.00"),
        )

        self.assertEqual(
            summary["transfer_count"],
            0,
        )

    # =============================================================
    # Recent transactions
    # =============================================================

    def test_recent_transactions(self):

        transactions = list(
            get_recent_transactions(
                self.user,
            )
        )

        self.assertEqual(
            len(transactions),
            3,
        )

    def test_recent_transactions_limit(self):

        transactions = list(
            get_recent_transactions(
                self.user,
                limit=2,
            )
        )

        self.assertEqual(
            len(transactions),
            2,
        )

    # =============================================================
    # Recent transfers
    # =============================================================

    def test_recent_transfers(self):

        transfer = Transfer.objects.create(
            user=self.user,
            from_account=self.cash,
            to_account=self.revolut,
            amount_from=Decimal("40.00"),
            amount_to=Decimal("40.00"),
            from_currency=self.eur,
            to_currency=self.eur,
            exchange_rate=Decimal("1.0000000000"),
            occurred_at=timezone.now(),
        )

        transfers = list(
            get_recent_transfers(
                self.user,
            )
        )

        self.assertEqual(
            len(transfers),
            1,
        )

        self.assertEqual(
            transfers[0].id,
            transfer.id,
        )

    # =============================================================
    # Expenses by category
    # =============================================================

    def test_expenses_by_category(self):

        categories = list(
            get_expenses_by_category(
                self.user,
            )
        )

        self.assertEqual(
            len(categories),
            2,
        )

        totals = {
            item["category__name"]: item["total"]
            for item in categories
        }

        self.assertEqual(
            totals["Food & Drinks"],
            Decimal("50.00"),
        )

        self.assertEqual(
            totals["Shopping"],
            Decimal("100.00"),
        )

    # =============================================================
    # Transfers excluded from income/expenses
    # =============================================================

    def test_transfers_are_excluded_from_expenses_and_income(self):

        Transfer.objects.create(
            user=self.user,
            from_account=self.cash,
            to_account=self.revolut,
            amount_from=Decimal("200.00"),
            amount_to=Decimal("200.00"),
            from_currency=self.eur,
            to_currency=self.eur,
            exchange_rate=Decimal("1.0000000000"),
            occurred_at=timezone.now(),
        )

        summary = get_dashboard_summary(
            self.user,
        )

        self.assertEqual(
            summary["income"],
            Decimal("500.00"),
        )

        self.assertEqual(
            summary["expenses"],
            Decimal("150.00"),
        )

        self.assertEqual(
            summary["net_cash_flow"],
            Decimal("350.00"),
        )

        self.assertEqual(
            summary["transfer_count"],
            1,
        )


class DashboardCurrencyTests(TestCase):

    def setUp(self):
        self.eur = Currency.objects.get(
            code="EUR",
        )

        self.gbp = Currency.objects.get(
            code="GBP",
        )

        self.usd = Currency.objects.get(
            code="USD",
        )

        self.user = User.objects.create_user(
            username="currency_dashboard_user",
            email="currency_dashboard@example.com",
            password="StrongPassword123!",
            base_currency=self.eur,
            language="en",
            is_email_verified=True,
            two_fa_enabled=True,
        )

        Profile.objects.create(
            user=self.user,
            country="Bulgaria",
        )


    def test_same_currency_conversion(self):

        result = convert_amount(
            amount=Decimal("100.00"),
            from_currency=self.eur,
            to_currency=self.eur,
        )

        self.assertEqual(
            result,
            Decimal("100.00"),
        )


    def test_gbp_to_eur_conversion(self):

        ExchangeRate.objects.create(
            from_currency=self.gbp,
            to_currency=self.eur,
            rate=Decimal("1.1680000000"),
            valid_at=timezone.now(),
            source="test",
        )

        result = convert_amount(
            amount=Decimal("100.00"),
            from_currency=self.gbp,
            to_currency=self.eur,
        )

        self.assertEqual(
            result,
            Decimal("116.800000000000"),
        )


    def test_total_balance_uses_base_currency(self):

        Account.objects.create(
            user=self.user,
            name="Cash",
            emoji="💵",
            color="#3498DB",
            currency=self.eur,
            opening_balance=500,
            current_balance=500,
        )

        Account.objects.create(
            user=self.user,
            name="GBP Account",
            emoji="💷",
            color="#9B59B6",
            currency=self.gbp,
            opening_balance=100,
            current_balance=100,
        )

        ExchangeRate.objects.create(
            from_currency=self.gbp,
            to_currency=self.eur,
            rate=Decimal("1.1680000000"),
            valid_at=timezone.now(),
            source="test",
        )

        result = get_total_balance(
            self.user,
        )

        self.assertEqual(
            result["total"],
            Decimal("616.800000000000"),
        )


    def test_missing_exchange_rate(self):

        Account.objects.create(
            user=self.user,
            name="GBP Account",
            emoji="💷",
            color="#9B59B6",
            currency=self.gbp,
            opening_balance=100,
            current_balance=100,
        )

        result = get_total_balance(
            self.user,
        )

        self.assertEqual(
            result["total"],
            Decimal("0"),
        )

        self.assertEqual(
            len(result["missing_rates"]),
            1,
        )


class DashboardMultiCurrencyTests(TestCase):

    def setUp(self):
        self.eur = Currency.objects.get(
            code="EUR",
        )

        self.gbp = Currency.objects.get(
            code="GBP",
        )

        self.usd = Currency.objects.get(
            code="USD",
        )

        self.user = User.objects.create_user(
            username="multi_currency_user",
            email="multi_currency@example.com",
            password="StrongPassword123!",
            base_currency=self.eur,
            language="en",
            is_email_verified=True,
            two_fa_enabled=True,
        )

        Profile.objects.create(
            user=self.user,
            country="Bulgaria",
        )

        # ---------------------------------------------------------
        # Default categories
        # ---------------------------------------------------------

        self.food = Category.objects.get(
            name="Food & Drinks",
            type=Category.EXPENSE,
            is_default=True,
        )

        self.income_category = Category.objects.get(
            name="Income",
            type=Category.INCOME,
            is_default=True,
        )

        # ---------------------------------------------------------
        # Default subcategories
        # ---------------------------------------------------------

        self.groceries = Subcategory.objects.get(
            category=self.food,
            name="Groceries",
            is_default=True,
        )

        self.wage = Subcategory.objects.get(
            category=self.income_category,
            name="Wage",
            is_default=True,
        )


    def test_total_balance_with_eur_gbp_and_usd(self):
        """
        Total balance must convert all account balances
        into the user's base currency.
        """

        Account.objects.create(
            user=self.user,
            name="Cash",
            emoji="💶",
            color="#3498DB",
            currency=self.eur,
            opening_balance=Decimal("100.00"),
            current_balance=Decimal("100.00"),
        )

        Account.objects.create(
            user=self.user,
            name="GBP Account",
            emoji="💷",
            color="#9B59B6",
            currency=self.gbp,
            opening_balance=Decimal("100.00"),
            current_balance=Decimal("100.00"),
        )

        Account.objects.create(
            user=self.user,
            name="USD Account",
            emoji="💵",
            color="#16A34A",
            currency=self.usd,
            opening_balance=Decimal("100.00"),
            current_balance=Decimal("100.00"),
        )

        now = timezone.now()

        ExchangeRate.objects.create(
            from_currency=self.gbp,
            to_currency=self.eur,
            rate=Decimal("1.1680000000"),
            valid_at=now,
            source="test",
        )

        ExchangeRate.objects.create(
            from_currency=self.usd,
            to_currency=self.eur,
            rate=Decimal("0.9200000000"),
            valid_at=now,
            source="test",
        )

        result = get_total_balance(
            self.user,
        )

        self.assertEqual(
            result["total"],
            Decimal("308.8000"),
        )

        self.assertEqual(
            len(result["missing_rates"]),
            0,
        )


    def test_historical_exchange_rate_is_used(self):
        """
        A transaction must use the exchange rate that was
        valid at the time of the transaction.
        """

        now = timezone.now()

        old_rate_time = now - timedelta(days=2)
        new_rate_time = now - timedelta(days=1)

        ExchangeRate.objects.create(
            from_currency=self.gbp,
            to_currency=self.eur,
            rate=Decimal("1.1000000000"),
            valid_at=old_rate_time,
            source="test-old",
        )

        ExchangeRate.objects.create(
            from_currency=self.gbp,
            to_currency=self.eur,
            rate=Decimal("1.1680000000"),
            valid_at=new_rate_time,
            source="test-new",
        )

        transaction_time = now

        rate = get_exchange_rate(
            from_currency=self.gbp,
            to_currency=self.eur,
            valid_at=transaction_time,
        )

        self.assertEqual(
            rate,
            Decimal("1.1680000000"),
        )


    def test_historical_transaction_is_converted_using_correct_rate(self):
        """
        A GBP transaction must be converted using the exchange
        rate that was valid when the transaction occurred.
        """

        account = Account.objects.create(
            user=self.user,
            name="GBP Account",
            emoji="💷",
            color="#9B59B6",
            currency=self.gbp,
            opening_balance=Decimal("100.00"),
            current_balance=Decimal("100.00"),
        )

        category = Category.objects.get(
            name="Food & Drinks",
            type=Category.EXPENSE,
            is_default=True,
        )

        subcategory = Subcategory.objects.get(
            name="Groceries",
            category=category,
            is_default=True,
        )

        now = timezone.now()

        transaction_time = now - timedelta(days=1)

        ExchangeRate.objects.create(
            from_currency=self.gbp,
            to_currency=self.eur,
            rate=Decimal("1.1000000000"),
            valid_at=now - timedelta(days=2),
            source="test-old",
        )

        ExchangeRate.objects.create(
            from_currency=self.gbp,
            to_currency=self.eur,
            rate=Decimal("1.2000000000"),
            valid_at=transaction_time,
            source="test-historical",
        )

        ExchangeRate.objects.create(
            from_currency=self.gbp,
            to_currency=self.eur,
            rate=Decimal("1.3000000000"),
            valid_at=now,
            source="test-new",
        )

        Transaction.objects.create(
            user=self.user,
            account=account,
            type=Transaction.EXPENSE,
            category=category,
            subcategory=subcategory,
            amount=Decimal("100.00"),
            currency=self.gbp,
            occurred_at=transaction_time,
            person="Test Person",
            description="Historical currency test",
        )

        summary = get_dashboard_summary(
            self.user,
        )

        self.assertEqual(
            summary["expenses"],
            Decimal("120.0000"),
        )


    def test_inverse_exchange_rate_is_supported(self):
        """
        If a direct GBP -> EUR rate does not exist,
        the service can use EUR -> GBP as an inverse rate.
        """

        now = timezone.now()

        ExchangeRate.objects.create(
            from_currency=self.eur,
            to_currency=self.gbp,
            rate=Decimal("0.8000000000"),
            valid_at=now,
            source="test-inverse",
        )

        rate = get_exchange_rate(
            from_currency=self.gbp,
            to_currency=self.eur,
            valid_at=now,
        )

        self.assertEqual(
            rate,
            Decimal("1.25"),
        )

        converted = convert_amount(
            amount=Decimal("100.00"),
            from_currency=self.gbp,
            to_currency=self.eur,
            valid_at=now,
        )

        self.assertEqual(
            converted,
            Decimal("125.0000000000"),
        )


    def test_monthly_income_expenses_returns_12_months(self):
        result = get_monthly_income_expenses(
            self.user,
            months=12,
        )

        self.assertEqual(
            len(result["months"]),
            12,
        )

        for month in result["months"]:
            self.assertEqual(
                month["income"],
                Decimal("0"),
            )

            self.assertEqual(
                month["expenses"],
                Decimal("0"),
            )


    def test_monthly_income_expenses_groups_transactions_by_month(self):
        occurred_at = timezone.make_aware(
            datetime(
                2026,
                9,
                10,
                12,
                0,
            )
        )

        cash = Account.objects.create(
            user=self.user,
            name="Cash",
            emoji="💶",
            color="#3498DB",
            currency=self.eur,
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
        )

        create_income(
            user=self.user,
            account=cash,
            category=self.income_category,
            subcategory=self.wage,
            amount=Decimal("500.00"),
            currency=self.eur,
            occurred_at=occurred_at,
        )

        create_expense(
            user=self.user,
            account=cash,
            category=self.food,
            subcategory=self.groceries,
            amount=Decimal("50.00"),
            currency=self.eur,
            occurred_at=occurred_at,
        )

        result = get_monthly_income_expenses(
            self.user,
            months=1,
        )

        month = result["months"][0]

        self.assertEqual(
            month["income"],
            Decimal("500.0000"),
        )

        self.assertEqual(
            month["expenses"],
            Decimal("50.0000"),
        )


    def test_monthly_income_expenses_uses_historical_exchange_rate(self):
        occurred_at = timezone.make_aware(
            datetime(
                2026,
                8,
                15,
                12,
                0,
            )
        )

        gbp_account = Account.objects.create(
            user=self.user,
            name="GBP Account",
            emoji="💷",
            color="#9B59B6",
            currency=self.gbp,
            opening_balance=Decimal("500.00"),
            current_balance=Decimal("500.00"),
        )

        ExchangeRate.objects.create(
            from_currency=self.gbp,
            to_currency=self.eur,
            rate=Decimal("1.1500000000"),
            valid_at=occurred_at - timedelta(days=1),
            source="test",
        )

        create_income(
            user=self.user,
            account=gbp_account,
            category=self.income_category,
            subcategory=self.wage,
            amount=Decimal("100.00"),
            currency=self.gbp,
            occurred_at=occurred_at,
        )

        result = get_monthly_income_expenses(
            self.user,
            months=12,
        )

        august = next(
            month
            for month in result["months"]
            if month["month"] == "2026-08"
        )

        self.assertEqual(
            august["income"],
            Decimal("115.0000"),
        )


    def test_monthly_income_expenses_excludes_transfers(self):
        occurred_at = timezone.make_aware(
            datetime(
                2026,
                9,
                10,
                12,
                0,
            )
        )

        cash = Account.objects.create(
            user=self.user,
            name="Cash",
            emoji="💶",
            color="#3498DB",
            currency=self.eur,
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
        )

        revolut = Account.objects.create(
            user=self.user,
            name="Revolut",
            emoji="💳",
            color="#9B59B6",
            currency=self.eur,
            opening_balance=Decimal("500.00"),
            current_balance=Decimal("500.00"),
        )

        create_transfer(
            user=self.user,
            from_account=cash,
            to_account=revolut,
            amount_from=Decimal("100.00"),
            amount_to=Decimal("100.00"),
            from_currency=self.eur,
            to_currency=self.eur,
            exchange_rate=Decimal("1.0000000000"),
            occurred_at=occurred_at,
        )

        result = get_monthly_income_expenses(
            self.user,
            months=1,
        )

        month = result["months"][0]

        self.assertEqual(
            month["income"],
            Decimal("0"),
        )

        self.assertEqual(
            month["expenses"],
            Decimal("0"),
        )