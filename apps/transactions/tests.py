from decimal import Decimal
from datetime import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Account
from apps.categories.models import Category, Subcategory
from apps.core.models import Currency
from apps.transactions.models import Transaction, Transfer
from apps.users.models import User, Profile

from apps.transactions.services import (
    create_expense,
    create_income,
    create_transfer,
    update_transaction,
    delete_transaction,
    update_transfer,
    delete_transfer,
    get_transaction_history,
)


class TransactionServicesTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Currencies
        cls.eur = Currency.objects.get(code="EUR")
        cls.gbp = Currency.objects.get(code="GBP")

        # User
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123!",
            base_currency=cls.eur,
        )

        # Categories
        cls.expense_category = Category.objects.get(
            name="Food & Drinks",
            type=Category.EXPENSE,
        )

        cls.expense_subcategory = Subcategory.objects.get(
            category=cls.expense_category,
            name="Groceries",
        )

        cls.income_category = Category.objects.get(
            name="Income",
            type=Category.INCOME,
        )

        cls.income_subcategory = Subcategory.objects.get(
            category=cls.income_category,
            name="Wage",
        )

        # Accounts
        cls.cash = Account.objects.create(
            user=cls.user,
            name="Cash",
            emoji="💵",
            color="#3498DB",
            currency=cls.eur,
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
        )

        cls.revolut = Account.objects.create(
            user=cls.user,
            name="Revolut",
            emoji="💳",
            color="#9B59B6",
            currency=cls.eur,
            opening_balance=Decimal("100.00"),
            current_balance=Decimal("100.00"),
        )

        cls.gbp_account = Account.objects.create(
            user=cls.user,
            name="GBP Account",
            emoji="💷",
            color="#2ECC71",
            currency=cls.gbp,
            opening_balance=Decimal("500.00"),
            current_balance=Decimal("500.00"),
        )

    def test_create_expense_decreases_balance(self):
        expense = create_expense(
            user=self.user,
            account=self.cash,
            category=self.expense_category,
            subcategory=self.expense_subcategory,
            amount=Decimal("100.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
            description="Weekly groceries",
        )

        self.cash.refresh_from_db()

        self.assertEqual(
            expense.type,
            Transaction.EXPENSE,
        )

        self.assertEqual(
            expense.amount,
            Decimal("100.00"),
        )

        self.assertEqual(
            self.cash.current_balance,
            Decimal("900.00"),
        )

        self.assertEqual(
            Transaction.objects.count(),
            1,
        )

    def test_create_income_increases_balance(self):
        income = create_income(
            user=self.user,
            account=self.cash,
            category=self.income_category,
            subcategory=self.income_subcategory,
            amount=Decimal("500.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
            description="Salary",
        )

        self.cash.refresh_from_db()

        self.assertEqual(
            income.type,
            Transaction.INCOME,
        )

        self.assertEqual(
            income.amount,
            Decimal("500.00"),
        )

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1500.00"),
        )

        self.assertEqual(
            Transaction.objects.count(),
            1,
        )

    def test_create_transfer_updates_both_balances(self):
        transfer = create_transfer(
            user=self.user,
            from_account=self.cash,
            to_account=self.revolut,
            amount_from=Decimal("100.00"),
            amount_to=Decimal("100.00"),
            from_currency=self.eur,
            to_currency=self.eur,
            exchange_rate=Decimal("1.0000000000"),
            occurred_at=timezone.now(),
            description="Move money to Revolut",
        )

        self.cash.refresh_from_db()
        self.revolut.refresh_from_db()

        self.assertEqual(
            transfer.amount_from,
            Decimal("100.00"),
        )

        self.assertEqual(
            transfer.amount_to,
            Decimal("100.00"),
        )

        self.assertEqual(
            self.cash.current_balance,
            Decimal("900.00"),
        )

        self.assertEqual(
            self.revolut.current_balance,
            Decimal("200.00"),
        )

        self.assertEqual(
            Transfer.objects.count(),
            1,
        )

    def test_create_transfer_with_exchange_rate(self):
        transfer = create_transfer(
            user=self.user,
            from_account=self.gbp_account,
            to_account=self.cash,
            amount_from=Decimal("100.00"),
            amount_to=Decimal("116.80"),
            from_currency=self.gbp,
            to_currency=self.eur,
            exchange_rate=Decimal("1.1680000000"),
            occurred_at=timezone.now(),
            description="GBP to EUR",
        )

        self.gbp_account.refresh_from_db()
        self.cash.refresh_from_db()

        self.assertEqual(
            transfer.exchange_rate,
            Decimal("1.1680000000"),
        )

        self.assertEqual(
            self.gbp_account.current_balance,
            Decimal("400.00"),
        )

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1116.80"),
        )

    def test_expense_cannot_use_income_category(self):
        with self.assertRaises(ValidationError):
            create_expense(
                user=self.user,
                account=self.cash,
                category=self.income_category,
                subcategory=self.income_subcategory,
                amount=Decimal("50.00"),
                currency=self.eur,
                occurred_at=timezone.now(),
            )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1000.00"),
        )

        self.assertEqual(
            Transaction.objects.count(),
            0,
        )

    def test_income_cannot_use_expense_category(self):
        with self.assertRaises(ValidationError):
            create_income(
                user=self.user,
                account=self.cash,
                category=self.expense_category,
                subcategory=self.expense_subcategory,
                amount=Decimal("50.00"),
                currency=self.eur,
                occurred_at=timezone.now(),
            )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1000.00"),
        )

        self.assertEqual(
            Transaction.objects.count(),
            0,
        )

    def test_negative_expense_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_expense(
                user=self.user,
                account=self.cash,
                category=self.expense_category,
                subcategory=self.expense_subcategory,
                amount=Decimal("-50.00"),
                currency=self.eur,
                occurred_at=timezone.now(),
            )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1000.00"),
        )

        self.assertEqual(
            Transaction.objects.count(),
            0,
        )

    def test_user_cannot_use_another_users_account(self):
        another_user = User.objects.create_user(
            username="anotheruser",
            email="another@example.com",
            password="TestPassword123!",
            base_currency=self.eur,
        )

        with self.assertRaises(ValidationError):
            create_expense(
                user=another_user,
                account=self.cash,
                category=self.expense_category,
                subcategory=self.expense_subcategory,
                amount=Decimal("50.00"),
                currency=self.eur,
                occurred_at=timezone.now(),
            )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1000.00"),
        )

    def test_wrong_transaction_currency_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_expense(
                user=self.user,
                account=self.cash,
                category=self.expense_category,
                subcategory=self.expense_subcategory,
                amount=Decimal("50.00"),
                currency=self.gbp,
                occurred_at=timezone.now(),
            )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1000.00"),
        )

    def test_transfer_between_same_account_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_transfer(
                user=self.user,
                from_account=self.cash,
                to_account=self.cash,
                amount_from=Decimal("100.00"),
                amount_to=Decimal("100.00"),
                from_currency=self.eur,
                to_currency=self.eur,
                exchange_rate=Decimal("1.0000000000"),
                occurred_at=timezone.now(),
            )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1000.00"),
        )

        self.assertEqual(
            Transfer.objects.count(),
            0,
        )
    
    def test_update_expense_changes_balance_correctly(self):
        expense = create_expense(
            user=self.user,
            account=self.cash,
            category=self.expense_category,
            subcategory=self.expense_subcategory,
            amount=Decimal("100.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
            description="Old amount",
        )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("900.00"),
        )

        update_transaction(
            user=self.user,
            transaction_id=expense.id,
            account=self.cash,
            category=self.expense_category,
            subcategory=self.expense_subcategory,
            amount=Decimal("150.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
            description="New amount",
        )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("850.00"),
        )

        expense.refresh_from_db()

        self.assertEqual(
            expense.amount,
            Decimal("150.00"),
        )

        self.assertEqual(
            expense.description,
            "New amount",
        )


    def test_update_income_changes_balance_correctly(self):
        income = create_income(
            user=self.user,
            account=self.cash,
            category=self.income_category,
            subcategory=self.income_subcategory,
            amount=Decimal("500.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
        )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1500.00"),
        )

        update_transaction(
            user=self.user,
            transaction_id=income.id,
            account=self.cash,
            category=self.income_category,
            subcategory=self.income_subcategory,
            amount=Decimal("300.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
        )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1300.00"),
        )

        income.refresh_from_db()

        self.assertEqual(
            income.amount,
            Decimal("300.00"),
        )


    def test_delete_expense_restores_balance(self):
        expense = create_expense(
            user=self.user,
            account=self.cash,
            category=self.expense_category,
            subcategory=self.expense_subcategory,
            amount=Decimal("100.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
        )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("900.00"),
        )

        delete_transaction(
            user=self.user,
            transaction_id=expense.id,
        )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1000.00"),
        )

        self.assertEqual(
            Transaction.objects.count(),
            0,
        )


    def test_delete_income_restores_balance(self):
        income = create_income(
            user=self.user,
            account=self.cash,
            category=self.income_category,
            subcategory=self.income_subcategory,
            amount=Decimal("500.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
        )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1500.00"),
        )

        delete_transaction(
            user=self.user,
            transaction_id=income.id,
        )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1000.00"),
        )

        self.assertEqual(
            Transaction.objects.count(),
            0,
        )


    def test_user_cannot_update_another_users_transaction(self):
        expense = create_expense(
            user=self.user,
            account=self.cash,
            category=self.expense_category,
            subcategory=self.expense_subcategory,
            amount=Decimal("100.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
        )

        another_user = User.objects.create_user(
            username="anotheruser",
            email="another@example.com",
            password="TestPassword123!",
            base_currency=self.eur,
        )

        with self.assertRaises(Transaction.DoesNotExist):
            update_transaction(
                user=another_user,
                transaction_id=expense.id,
                account=self.cash,
                category=self.expense_category,
                subcategory=self.expense_subcategory,
                amount=Decimal("200.00"),
                currency=self.eur,
                occurred_at=timezone.now(),
            )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("900.00"),
        )


    def test_user_cannot_delete_another_users_transaction(self):
        expense = create_expense(
            user=self.user,
            account=self.cash,
            category=self.expense_category,
            subcategory=self.expense_subcategory,
            amount=Decimal("100.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
        )

        another_user = User.objects.create_user(
            username="anotheruser",
            email="another@example.com",
            password="TestPassword123!",
            base_currency=self.eur,
        )

        with self.assertRaises(Transaction.DoesNotExist):
            delete_transaction(
                user=another_user,
                transaction_id=expense.id,
            )

        self.cash.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("900.00"),
        )

        self.assertEqual(
            Transaction.objects.count(),
            1,
        )

    def test_invalid_exchange_rate_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_transfer(
                user=self.user,
                from_account=self.gbp_account,
                to_account=self.cash,
                amount_from=Decimal("100.00"),
                amount_to=Decimal("116.80"),
                from_currency=self.gbp,
                to_currency=self.eur,
                exchange_rate=Decimal("2.0000000000"),
                occurred_at=timezone.now(),
            )

        self.gbp_account.refresh_from_db()
        self.cash.refresh_from_db()

        self.assertEqual(
            self.gbp_account.current_balance,
            Decimal("500.00"),
        )

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1000.00"),
        )

        self.assertEqual(
            Transfer.objects.count(),
            0,
        )
    

    def test_update_transfer_updates_balances(self):
        transfer = create_transfer(
            user=self.user,
            from_account=self.cash,
            to_account=self.revolut,
            amount_from=Decimal("100.00"),
            amount_to=Decimal("100.00"),
            from_currency=self.eur,
            to_currency=self.eur,
            exchange_rate=Decimal("1.0000000000"),
            occurred_at=timezone.now(),
            description="Old transfer",
        )

        self.cash.refresh_from_db()
        self.revolut.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("900.00"),
        )

        self.assertEqual(
            self.revolut.current_balance,
            Decimal("200.00"),
        )

        updated_transfer = update_transfer(
            user=self.user,
            transfer_id=transfer.id,
            from_account=self.cash,
            to_account=self.revolut,
            amount_from=Decimal("150.00"),
            amount_to=Decimal("150.00"),
            from_currency=self.eur,
            to_currency=self.eur,
            exchange_rate=Decimal("1.0000000000"),
            occurred_at=timezone.now(),
            description="Updated transfer",
        )

        self.cash.refresh_from_db()
        self.revolut.refresh_from_db()

        self.assertEqual(
            updated_transfer.amount_from,
            Decimal("150.00"),
        )

        self.assertEqual(
            updated_transfer.amount_to,
            Decimal("150.00"),
        )

        self.assertEqual(
            updated_transfer.description,
            "Updated transfer",
        )

        self.assertEqual(
            self.cash.current_balance,
            Decimal("850.00"),
        )

        self.assertEqual(
            self.revolut.current_balance,
            Decimal("250.00"),
        )


    def test_delete_transfer_restores_balances(self):
        transfer = create_transfer(
            user=self.user,
            from_account=self.cash,
            to_account=self.revolut,
            amount_from=Decimal("100.00"),
            amount_to=Decimal("100.00"),
            from_currency=self.eur,
            to_currency=self.eur,
            exchange_rate=Decimal("1.0000000000"),
            occurred_at=timezone.now(),
            description="Transfer to delete",
        )

        self.cash.refresh_from_db()
        self.revolut.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("900.00"),
        )

        self.assertEqual(
            self.revolut.current_balance,
            Decimal("200.00"),
        )

        delete_transfer(
            user=self.user,
            transfer_id=transfer.id,
        )

        self.cash.refresh_from_db()
        self.revolut.refresh_from_db()

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1000.00"),
        )

        self.assertEqual(
            self.revolut.current_balance,
            Decimal("100.00"),
        )

        self.assertEqual(
            Transfer.objects.count(),
            0,
        )


    def test_update_transfer_with_exchange_rate(self):
        transfer = create_transfer(
            user=self.user,
            from_account=self.gbp_account,
            to_account=self.cash,
            amount_from=Decimal("100.00"),
            amount_to=Decimal("116.80"),
            from_currency=self.gbp,
            to_currency=self.eur,
            exchange_rate=Decimal("1.1680000000"),
            occurred_at=timezone.now(),
            description="GBP transfer",
        )

        self.gbp_account.refresh_from_db()
        self.cash.refresh_from_db()

        self.assertEqual(
            self.gbp_account.current_balance,
            Decimal("400.00"),
        )

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1116.80"),
        )

        updated_transfer = update_transfer(
            user=self.user,
            transfer_id=transfer.id,
            from_account=self.gbp_account,
            to_account=self.cash,
            amount_from=Decimal("50.00"),
            amount_to=Decimal("58.40"),
            from_currency=self.gbp,
            to_currency=self.eur,
            exchange_rate=Decimal("1.1680000000"),
            occurred_at=timezone.now(),
            description="Updated GBP transfer",
        )

        self.gbp_account.refresh_from_db()
        self.cash.refresh_from_db()

        self.assertEqual(
            updated_transfer.amount_from,
            Decimal("50.00"),
        )

        self.assertEqual(
            updated_transfer.amount_to,
            Decimal("58.40"),
        )

        self.assertEqual(
            self.gbp_account.current_balance,
            Decimal("450.00"),
        )

        self.assertEqual(
            self.cash.current_balance,
            Decimal("1058.40"),
        )


class TransactionHistoryTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.eur = Currency.objects.get(code="EUR")

        cls.user = User.objects.create_user(
            username="history_user",
            email="history@example.com",
            password="TestPassword123!",
            base_currency=cls.eur,
        )

        cls.expense_category = Category.objects.get(
            name="Food & Drinks",
            type=Category.EXPENSE,
        )

        cls.expense_subcategory = Subcategory.objects.get(
            category=cls.expense_category,
            name="Groceries",
        )

        cls.income_category = Category.objects.get(
            name="Income",
            type=Category.INCOME,
        )

        cls.income_subcategory = Subcategory.objects.get(
            category=cls.income_category,
            name="Wage",
        )

        cls.account = Account.objects.create(
            user=cls.user,
            name="Cash",
            currency=cls.eur,
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
        )

        cls.second_account = Account.objects.create(
            user=cls.user,
            name="Bank",
            currency=cls.eur,
            opening_balance=Decimal("500.00"),
            current_balance=Decimal("500.00"),
        )

    def test_history_contains_transactions_and_transfers(self):
        expense = create_expense(
            user=self.user,
            account=self.account,
            category=self.expense_category,
            subcategory=self.expense_subcategory,
            amount=Decimal("50.00"),
            currency=self.eur,
            occurred_at=timezone.make_aware(
                datetime(2026, 9, 10, 12, 0)
            ),
            description="Groceries",
        )

        income = create_income(
            user=self.user,
            account=self.account,
            category=self.income_category,
            subcategory=self.income_subcategory,
            amount=Decimal("500.00"),
            currency=self.eur,
            occurred_at=timezone.make_aware(
                datetime(2026, 9, 11, 12, 0)
            ),
            description="Salary",
        )

        transfer = create_transfer(
            user=self.user,
            from_account=self.account,
            to_account=self.second_account,
            amount_from=Decimal("100.00"),
            amount_to=Decimal("100.00"),
            from_currency=self.eur,
            to_currency=self.eur,
            exchange_rate=Decimal("1.0000000000"),
            occurred_at=timezone.make_aware(
                datetime(2026, 9, 12, 12, 0)
            ),
            description="Move money",
        )

        history = get_transaction_history(user=self.user)

        self.assertEqual(len(history), 3)

        self.assertEqual(history[0]["kind"], "transfer")
        self.assertEqual(history[0]["id"], transfer.id)

        self.assertEqual(history[1]["kind"], "income")
        self.assertEqual(history[1]["id"], income.id)

        self.assertEqual(history[2]["kind"], "expense")
        self.assertEqual(history[2]["id"], expense.id)

    def test_history_is_sorted_newest_first(self):
        create_expense(
            user=self.user,
            account=self.account,
            category=self.expense_category,
            subcategory=self.expense_subcategory,
            amount=Decimal("10.00"),
            currency=self.eur,
            occurred_at=timezone.make_aware(
                datetime(2026, 9, 1, 10, 0)
            ),
        )

        create_income(
            user=self.user,
            account=self.account,
            category=self.income_category,
            subcategory=self.income_subcategory,
            amount=Decimal("20.00"),
            currency=self.eur,
            occurred_at=timezone.make_aware(
                datetime(2026, 9, 5, 10, 0)
            ),
        )

        history = get_transaction_history(user=self.user)

        self.assertEqual(len(history), 2)
        self.assertGreaterEqual(
            history[0]["occurred_at"],
            history[1]["occurred_at"],
        )

    def test_history_contains_only_current_users_data(self):
        other_user = User.objects.create_user(
            username="other_history_user",
            email="other_history@example.com",
            password="TestPassword123!",
            base_currency=self.eur,
        )

        other_account = Account.objects.create(
            user=other_user,
            name="Other Cash",
            currency=self.eur,
            opening_balance=Decimal("100.00"),
            current_balance=Decimal("100.00"),
        )

        create_expense(
            user=other_user,
            account=other_account,
            category=self.expense_category,
            subcategory=self.expense_subcategory,
            amount=Decimal("25.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
        )

        history = get_transaction_history(user=self.user)

        self.assertEqual(history, [])


class TransactionListFilterTests(TestCase):

    def setUp(self):
        self.client = Client()

        self.eur = Currency.objects.get(
            code="EUR",
        )

        self.user = User.objects.create_user(
            username="filter_user",
            email="filter@example.com",
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

        self.cash = Account.objects.create(
            user=self.user,
            name="Cash",
            emoji="💵",
            color="#3498DB",
            currency=self.eur,
            opening_balance=1000,
            current_balance=1000,
        )

        self.revolut = Account.objects.create(
            user=self.user,
            name="Revolut",
            emoji="💳",
            color="#9B59B6",
            currency=self.eur,
            opening_balance=500,
            current_balance=500,
        )

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

        self.expense = Transaction.objects.create(
            user=self.user,
            account=self.cash,
            type=Transaction.EXPENSE,
            category=self.food,
            subcategory=self.groceries,
            amount=Decimal("50.00"),
            currency=self.eur,
            occurred_at=timezone.make_aware(
                datetime(2026, 9, 10, 10, 0)
            ),
            person="Stefan",
            description="Groceries shopping",
        )

        self.second_expense = Transaction.objects.create(
            user=self.user,
            account=self.revolut,
            type=Transaction.EXPENSE,
            category=self.shopping,
            subcategory=self.clothes,
            amount=Decimal("100.00"),
            currency=self.eur,
            occurred_at=timezone.make_aware(
                datetime(2026, 9, 8, 10, 0)
            ),
            person="Mum",
            description="New clothes",
        )

        self.income = Transaction.objects.create(
            user=self.user,
            account=self.cash,
            type=Transaction.INCOME,
            category=self.income_category,
            subcategory=self.wage,
            amount=Decimal("500.00"),
            currency=self.eur,
            occurred_at=timezone.make_aware(
                datetime(2026, 9, 9, 10, 0)
            ),
            person="Employer",
            description="September salary",
        )

        self.transfer = Transfer.objects.create(
            user=self.user,
            from_account=self.cash,
            to_account=self.revolut,
            amount_from=Decimal("200.00"),
            amount_to=Decimal("200.00"),
            from_currency=self.eur,
            to_currency=self.eur,
            exchange_rate=Decimal("1.0000000000"),
            occurred_at=timezone.make_aware(
                datetime(2026, 9, 7, 10, 0)
            ),
            description="Move money to Revolut",
        )

        self.client.login(
            username="filter_user",
            password="StrongPassword123!",
        )
    
        def test_transaction_list_loads_successfully(self):
            response = self.client.get(
                reverse("transaction-list")
            )

            self.assertEqual(
                response.status_code,
                200,
            )

            self.assertContains(
                response,
                "Groceries shopping",
            )

            self.assertContains(
                response,
                "September salary",
            )

            self.assertContains(
                response,
                "Move money to Revolut",
            )
        
    def test_filter_by_expense(self):
        response = self.client.get(
            reverse("transaction-list"),
            {
                "kind": "expense",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Groceries shopping",
        )

        self.assertContains(
            response,
            "New clothes",
        )

        self.assertNotContains(
            response,
            "September salary",
        )

        self.assertNotContains(
            response,
            "Move money to Revolut",
        )


    def test_filter_by_income(self):
        response = self.client.get(
            reverse("transaction-list"),
            {
                "kind": "income",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "September salary",
        )

        self.assertNotContains(
            response,
            "Groceries shopping",
        )

        self.assertNotContains(
            response,
            "New clothes",
        )

        self.assertNotContains(
            response,
            "Move money to Revolut",
        )


    def test_filter_by_transfer(self):
        response = self.client.get(
            reverse("transaction-list"),
            {
                "kind": "transfer",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Move money to Revolut",
        )

        self.assertNotContains(
            response,
            "Groceries shopping",
        )

        self.assertNotContains(
            response,
            "September salary",
        )
    
    def test_filter_by_category(self):
        response = self.client.get(
            reverse("transaction-list"),
            {
                "category": self.food.id,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Groceries shopping",
        )

        self.assertNotContains(
            response,
            "New clothes",
        )

        self.assertNotContains(
            response,
            "September salary",
        )
    
    def test_filter_by_account(self):
        response = self.client.get(
            reverse("transaction-list"),
            {
                "account": self.revolut.id,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "New clothes",
        )

        self.assertNotContains(
            response,
            "Groceries shopping",
        )

        self.assertNotContains(
            response,
            "September salary",
        )
    
    def test_search_by_description(self):
        response = self.client.get(
            reverse("transaction-list"),
            {
                "search": "Groceries",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Groceries shopping",
        )

        self.assertNotContains(
            response,
            "September salary",
        )
    
    def test_search_by_person(self):
        response = self.client.get(
            reverse("transaction-list"),
            {
                "search": "Employer",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "September salary",
        )

        self.assertNotContains(
            response,
            "Groceries shopping",
        )
    
    def test_combined_filters(self):
        response = self.client.get(
            reverse("transaction-list"),
            {
                "kind": "expense",
                "category": self.food.id,
                "account": self.cash.id,
                "search": "Groceries",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Groceries shopping",
        )

        self.assertNotContains(
            response,
            "New clothes",
        )

        self.assertNotContains(
            response,
            "September salary",
        )

        self.assertNotContains(
            response,
            "Move money to Revolut",
        )
    
    def test_filter_by_date_from(self):
        response = self.client.get(
            reverse("transaction-list"),
            {
                "date_from": "2026-09-09",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Groceries shopping",
        )

        self.assertContains(
            response,
            "September salary",
        )

        self.assertNotContains(
            response,
            "New clothes",
        )

        self.assertNotContains(
            response,
            "Move money to Revolut",
        )
    
    def test_filter_by_date_to(self):
        response = self.client.get(
            reverse("transaction-list"),
            {
                "date_to": "2026-09-08",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "New clothes",
        )

        self.assertContains(
            response,
            "Move money to Revolut",
        )

        self.assertNotContains(
            response,
            "Groceries shopping",
        )

        self.assertNotContains(
            response,
            "September salary",
        )
    
    def test_transaction_list_requires_login(self):
        self.client.logout()

        response = self.client.get(
            reverse("transaction-list")
        )

        self.assertEqual(
            response.status_code,
            302,
        )