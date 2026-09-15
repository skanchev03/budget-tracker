from decimal import Decimal
from datetime import datetime

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.forms import (
    CreateAccountForm,
    UpdateAccountForm,
)
from apps.accounts.models import Account
from apps.categories.models import Category, Subcategory
from apps.accounts.services import (
    create_account,
    delete_account,
    get_account_history,
    get_user_account,
    get_user_accounts,
    reorder_accounts,
    update_account,
)
from apps.core.models import Currency
from apps.transactions.models import Transaction, Transfer
from apps.users.models import User


class AccountModelTests(TestCase):
    def setUp(self):
        self.eur = Currency.objects.get(code="EUR")
        self.gbp = Currency.objects.get(code="GBP")

        self.user = User.objects.create_user(
            username="accountuser",
            email="account@example.com",
            password="StrongPassword123!",
            base_currency=self.eur,
            language="bg",
        )

    def test_account_can_be_created(self):
        account = Account.objects.create(
            user=self.user,
            name="Cash",
            currency=self.eur,
            opening_balance=Decimal("100.00"),
            current_balance=Decimal("100.00"),
        )

        self.assertEqual(
            account.name,
            "Cash",
        )

        self.assertEqual(
            account.user,
            self.user,
        )

        self.assertEqual(
            account.currency,
            self.eur,
        )

    def test_default_values_are_applied(self):
        account = Account.objects.create(
            user=self.user,
            name="Cash",
            currency=self.eur,
        )

        self.assertEqual(
            account.emoji,
            "💰",
        )

        self.assertEqual(
            account.color,
            "#3498DB",
        )

        self.assertEqual(
            account.opening_balance,
            Decimal("0"),
        )

        self.assertEqual(
            account.current_balance,
            Decimal("0"),
        )

        self.assertEqual(
            account.display_order,
            0,
        )

        self.assertTrue(
            account.is_active,
        )

    def test_custom_values_are_saved(self):
        account = Account.objects.create(
            user=self.user,
            name="Revolut",
            emoji="📱",
            color="#FF5733",
            currency=self.gbp,
            opening_balance=Decimal("250.50"),
            current_balance=Decimal("300.75"),
            display_order=5,
            is_active=False,
        )

        self.assertEqual(account.emoji, "📱")
        self.assertEqual(account.color, "#FF5733")
        self.assertEqual(account.currency, self.gbp)
        self.assertEqual(
            account.opening_balance,
            Decimal("250.50"),
        )
        self.assertEqual(
            account.current_balance,
            Decimal("300.75"),
        )
        self.assertEqual(account.display_order, 5)
        self.assertFalse(account.is_active)

    def test_account_string_representation(self):
        account = Account.objects.create(
            user=self.user,
            name="Cash",
            currency=self.eur,
        )

        self.assertEqual(
            str(account),
            "💰 Cash",
        )

    def test_accounts_belong_to_user(self):
        second_user = User.objects.create_user(
            username="seconduser",
            email="second@example.com",
            password="StrongPassword123!",
            base_currency=self.eur,
            language="bg",
        )

        account_one = Account.objects.create(
            user=self.user,
            name="Cash",
            currency=self.eur,
        )

        account_two = Account.objects.create(
            user=second_user,
            name="Cash",
            currency=self.eur,
        )

        self.assertEqual(
            self.user.accounts.count(),
            1,
        )

        self.assertEqual(
            second_user.accounts.count(),
            1,
        )

        self.assertNotEqual(
            account_one.user,
            account_two.user,
        )

    def test_negative_balances_are_allowed(self):
        account = Account.objects.create(
            user=self.user,
            name="Bank",
            currency=self.eur,
            opening_balance=Decimal("-100.00"),
            current_balance=Decimal("-50.00"),
        )

        self.assertEqual(
            account.opening_balance,
            Decimal("-100.00"),
        )

        self.assertEqual(
            account.current_balance,
            Decimal("-50.00"),
        )

    def test_valid_hex_color_is_accepted(self):
        account = Account(
            user=self.user,
            name="Bank",
            currency=self.eur,
            color="#ABC123",
        )

        account.full_clean()

        account = Account.objects.create(
            user=self.user,
            name="Bank",
            currency=self.eur,
            color="#ABC123",
        )

        self.assertEqual(
            account.color,
            "#ABC123",
        )

    def test_invalid_hex_color_fails_validation(self):
        account = Account(
            user=self.user,
            name="Bank",
            currency=self.eur,
            color="blue",
        )

        with self.assertRaises(ValidationError):
            account.full_clean()

    def test_short_hex_color_fails_validation(self):
        account = Account(
            user=self.user,
            name="Bank",
            currency=self.eur,
            color="#12345",
        )

        with self.assertRaises(ValidationError):
            account.full_clean()

    def test_color_without_hash_fails_validation(self):
        account = Account(
            user=self.user,
            name="Bank",
            currency=self.eur,
            color="ABC123",
        )

        with self.assertRaises(ValidationError):
            account.full_clean()

    def test_accounts_are_ordered_by_display_order_and_name(self):
        Account.objects.create(
            user=self.user,
            name="Ziraat",
            currency=self.eur,
            display_order=2,
        )

        Account.objects.create(
            user=self.user,
            name="Cash",
            currency=self.eur,
            display_order=1,
        )

        Account.objects.create(
            user=self.user,
            name="Bank",
            currency=self.eur,
            display_order=1,
        )

        accounts = list(
            Account.objects.all()
        )

        self.assertEqual(
            [account.name for account in accounts],
            ["Bank", "Cash", "Ziraat"],
        )

    def test_currency_is_protected_from_deletion(self):
        account = Account.objects.create(
            user=self.user,
            name="Cash",
            currency=self.eur,
        )

        with self.assertRaises(IntegrityError):
            self.eur.delete()

        self.assertTrue(
            Account.objects.filter(
                pk=account.pk
            ).exists()
        )


class AccountServiceTests(TestCase):
    def setUp(self):
        self.eur = Currency.objects.get(code="EUR")
        self.gbp = Currency.objects.get(code="GBP")

        self.user = User.objects.create_user(
            username="serviceuser",
            email="service@example.com",
            password="StrongPassword123!",
            base_currency=self.eur,
            language="bg",
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="StrongPassword123!",
            base_currency=self.eur,
            language="bg",
        )

    def test_create_account(self):
        account = create_account(
            user=self.user,
            name="Cash",
            emoji="💰",
            color="#3498DB",
            currency=self.eur,
            opening_balance=Decimal("500.00"),
        )

        self.assertEqual(
            account.user,
            self.user,
        )

        self.assertEqual(
            account.name,
            "Cash",
        )

        self.assertEqual(
            account.currency,
            self.eur,
        )

        self.assertEqual(
            account.opening_balance,
            Decimal("500.00"),
        )

        self.assertEqual(
            account.current_balance,
            Decimal("500.00"),
        )

    def test_create_account_with_zero_opening_balance(self):
        account = create_account(
            user=self.user,
            name="Bank",
            currency=self.eur,
        )

        self.assertEqual(
            account.opening_balance,
            Decimal("0"),
        )

        self.assertEqual(
            account.current_balance,
            Decimal("0"),
        )

    def test_get_user_accounts_returns_only_active_user_accounts(self):
        active_account = Account.objects.create(
            user=self.user,
            name="Cash",
            currency=self.eur,
            is_active=True,
        )

        Account.objects.create(
            user=self.user,
            name="Old Account",
            currency=self.eur,
            is_active=False,
        )

        Account.objects.create(
            user=self.other_user,
            name="Other Cash",
            currency=self.eur,
            is_active=True,
        )

        accounts = list(
            get_user_accounts(self.user)
        )

        self.assertEqual(
            accounts,
            [active_account],
        )

    def test_get_user_account_returns_owned_account(self):
        account = Account.objects.create(
            user=self.user,
            name="Cash",
            currency=self.eur,
        )

        result = get_user_account(
            user=self.user,
            account_id=account.pk,
        )

        self.assertEqual(
            result,
            account,
        )

    def test_get_user_account_rejects_other_users_account(self):
        account = Account.objects.create(
            user=self.other_user,
            name="Other Cash",
            currency=self.eur,
        )

        with self.assertRaises(PermissionDenied):
            get_user_account(
                user=self.user,
                account_id=account.pk,
            )

    def test_get_user_account_rejects_nonexistent_account(self):
        with self.assertRaises(PermissionDenied):
            get_user_account(
                user=self.user,
                account_id=999999,
            )

    def test_update_account(self):
        account = Account.objects.create(
            user=self.user,
            name="Cash",
            emoji="💰",
            color="#3498DB",
            currency=self.eur,
            display_order=1,
        )

        updated_account = update_account(
            user=self.user,
            account_id=account.pk,
            name="Wallet",
            emoji="👛",
            color="#FF0000",
            display_order=5,
        )

        self.assertEqual(
            updated_account.name,
            "Wallet",
        )

        self.assertEqual(
            updated_account.emoji,
            "👛",
        )

        self.assertEqual(
            updated_account.color,
            "#FF0000",
        )

        self.assertEqual(
            updated_account.display_order,
            5,
        )

    def test_update_account_cannot_change_currency(self):
        account = Account.objects.create(
            user=self.user,
            name="Cash",
            currency=self.eur,
        )

        update_account(
            user=self.user,
            account_id=account.pk,
            name="Updated Cash",
        )

        account.refresh_from_db()

        self.assertEqual(
            account.currency,
            self.eur,
        )

    def test_update_account_rejects_other_users_account(self):
        account = Account.objects.create(
            user=self.other_user,
            name="Other Cash",
            currency=self.eur,
        )

        with self.assertRaises(PermissionDenied):
            update_account(
                user=self.user,
                account_id=account.pk,
                name="Hacked",
            )

    def test_update_account_does_not_change_balance(self):
        account = Account.objects.create(
            user=self.user,
            name="Cash",
            currency=self.eur,
            opening_balance=Decimal("500.00"),
            current_balance=Decimal("450.00"),
        )

        update_account(
            user=self.user,
            account_id=account.pk,
            name="Updated Cash",
        )

        account.refresh_from_db()

        self.assertEqual(
            account.opening_balance,
            Decimal("500.00"),
        )

        self.assertEqual(
            account.current_balance,
            Decimal("450.00"),
        )

    def test_delete_account(self):
        account = Account.objects.create(
            user=self.user,
            name="Cash",
            currency=self.eur,
        )

        delete_account(
            user=self.user,
            account_id=account.pk,
        )

        self.assertFalse(
            Account.objects.filter(
                pk=account.pk
            ).exists()
        )

    def test_delete_account_rejects_other_users_account(self):
        account = Account.objects.create(
            user=self.other_user,
            name="Other Cash",
            currency=self.eur,
        )

        with self.assertRaises(PermissionDenied):
            delete_account(
                user=self.user,
                account_id=account.pk,
            )

        self.assertTrue(
            Account.objects.filter(
                pk=account.pk
            ).exists()
        )


class AccountFormTests(TestCase):
    def setUp(self):
        self.eur = Currency.objects.get(code="EUR")
        self.gbp = Currency.objects.get(code="GBP")

    def test_create_account_form_is_valid_with_valid_data(self):
        form = CreateAccountForm(
            data={
                "name": "Cash",
                "emoji": "💰",
                "color": "#3498DB",
                "currency": self.eur.pk,
                "opening_balance": "500.00",
                "display_order": 1,
            }
        )

        self.assertTrue(form.is_valid())

    def test_create_account_form_has_currency_field(self):
        form = CreateAccountForm()

        self.assertIn(
            "currency",
            form.fields,
        )

    def test_create_account_form_default_emoji(self):
        form = CreateAccountForm()

        self.assertEqual(
            form.fields["emoji"].initial,
            "💰",
        )

    def test_create_account_form_default_color(self):
        form = CreateAccountForm()

        self.assertEqual(
            form.fields["color"].initial,
            "#3498DB",
        )

    def test_create_account_form_default_opening_balance(self):
        form = CreateAccountForm()

        self.assertEqual(
            form.fields["opening_balance"].initial,
            Decimal("0"),
        )

    def test_create_account_form_allows_negative_opening_balance(self):
        form = CreateAccountForm(
            data={
                "name": "Bank",
                "emoji": "🏦",
                "color": "#3498DB",
                "currency": self.eur.pk,
                "opening_balance": "-100.00",
                "display_order": 0,
            }
        )

        self.assertTrue(form.is_valid())

        self.assertEqual(
            form.cleaned_data["opening_balance"],
            Decimal("-100.00"),
        )

    def test_create_account_form_rejects_empty_name(self):
        form = CreateAccountForm(
            data={
                "name": "   ",
                "emoji": "💰",
                "color": "#3498DB",
                "currency": self.eur.pk,
                "opening_balance": "0",
                "display_order": 0,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "name",
            form.errors,
        )

    def test_create_account_form_rejects_invalid_color(self):
        form = CreateAccountForm(
            data={
                "name": "Cash",
                "emoji": "💰",
                "color": "blue",
                "currency": self.eur.pk,
                "opening_balance": "0",
                "display_order": 0,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "color",
            form.errors,
        )

    def test_create_account_form_rejects_short_hex_color(self):
        form = CreateAccountForm(
            data={
                "name": "Cash",
                "emoji": "💰",
                "color": "#12345",
                "currency": self.eur.pk,
                "opening_balance": "0",
                "display_order": 0,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "color",
            form.errors,
        )

    def test_create_account_form_normalizes_lowercase_hex_color(self):
        form = CreateAccountForm(
            data={
                "name": "Cash",
                "emoji": "💰",
                "color": "#abcdef",
                "currency": self.eur.pk,
                "opening_balance": "0",
                "display_order": 0,
            }
        )

        self.assertTrue(form.is_valid())

        self.assertEqual(
            form.cleaned_data["color"],
            "#ABCDEF",
        )

    def test_create_account_form_uses_default_emoji_when_empty(self):
        form = CreateAccountForm(
            data={
                "name": "Cash",
                "emoji": "",
                "color": "#3498DB",
                "currency": self.eur.pk,
                "opening_balance": "0",
                "display_order": 0,
            }
        )

        self.assertTrue(form.is_valid())

        self.assertEqual(
            form.cleaned_data["emoji"],
            "💰",
        )

    def test_create_account_form_uses_zero_when_opening_balance_is_empty(self):
        form = CreateAccountForm(
            data={
                "name": "Cash",
                "emoji": "💰",
                "color": "#3498DB",
                "currency": self.eur.pk,
                "opening_balance": "",
                "display_order": 0,
            }
        )

        self.assertTrue(form.is_valid())

        self.assertEqual(
            form.cleaned_data["opening_balance"],
            Decimal("0"),
        )

    def test_update_account_form_is_valid_with_valid_data(self):
        form = UpdateAccountForm(
            data={
                "name": "Updated Cash",
                "emoji": "👛",
                "color": "#FF0000",
                "display_order": 2,
                "is_active": True,
            }
        )

        self.assertTrue(form.is_valid())

    def test_update_account_form_does_not_have_currency_field(self):
        form = UpdateAccountForm()

        self.assertNotIn(
            "currency",
            form.fields,
        )

    def test_update_account_form_does_not_have_current_balance_field(self):
        form = UpdateAccountForm()

        self.assertNotIn(
            "current_balance",
            form.fields,
        )

    def test_update_account_form_rejects_empty_name(self):
        form = UpdateAccountForm(
            data={
                "name": "   ",
                "emoji": "💰",
                "color": "#3498DB",
                "display_order": 0,
                "is_active": True,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "name",
            form.errors,
        )

    def test_update_account_form_rejects_invalid_color(self):
        form = UpdateAccountForm(
            data={
                "name": "Cash",
                "emoji": "💰",
                "color": "not-a-color",
                "display_order": 0,
                "is_active": True,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "color",
            form.errors,
        )

    def test_update_account_form_normalizes_lowercase_hex_color(self):
        form = UpdateAccountForm(
            data={
                "name": "Cash",
                "emoji": "💰",
                "color": "#abcdef",
                "display_order": 0,
                "is_active": True,
            }
        )

        self.assertTrue(form.is_valid())

        self.assertEqual(
            form.cleaned_data["color"],
            "#ABCDEF",
        )

    def test_update_account_form_uses_default_emoji_when_empty(self):
        form = UpdateAccountForm(
            data={
                "name": "Cash",
                "emoji": "",
                "color": "#3498DB",
                "display_order": 0,
                "is_active": True,
            }
        )

        self.assertTrue(form.is_valid())

        self.assertEqual(
            form.cleaned_data["emoji"],
            "💰",
        )

class AccountHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.eur = Currency.objects.get(code="EUR")
        cls.gbp = Currency.objects.get(code="GBP")

        cls.user = User.objects.create_user(
            username="historyuser",
            email="history@example.com",
            password="StrongPassword123!",
            base_currency=cls.eur,
            language="bg",
        )

        cls.other_user = User.objects.create_user(
            username="otherhistoryuser",
            email="otherhistory@example.com",
            password="StrongPassword123!",
            base_currency=cls.eur,
            language="bg",
        )

        cls.expense_category = Category.objects.get(
            name="Food & Drinks",
            type=Category.EXPENSE,
            is_default=True,
        )

        cls.expense_subcategory = Subcategory.objects.get(
            category=cls.expense_category,
            name="Groceries",
            is_default=True,
        )

        cls.income_category = Category.objects.get(
            name="Income",
            type=Category.INCOME,
            is_default=True,
        )

        cls.income_subcategory = Subcategory.objects.get(
            category=cls.income_category,
            name="Wage",
            is_default=True,
        )

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

    def test_history_combines_transactions_and_transfers_in_chronological_order(self):
        expense_time = timezone.make_aware(
            datetime(2026, 9, 7, 10, 0)
        )

        income_time = timezone.make_aware(
            datetime(2026, 9, 8, 10, 0)
        )

        outgoing_transfer_time = timezone.make_aware(
            datetime(2026, 9, 9, 10, 0)
        )

        incoming_transfer_time = timezone.make_aware(
            datetime(2026, 9, 10, 10, 0)
        )

        Transaction.objects.create(
            user=self.user,
            account=self.cash,
            type=Transaction.EXPENSE,
            category=self.expense_category,
            subcategory=self.expense_subcategory,
            amount=Decimal("50.00"),
            currency=self.eur,
            occurred_at=expense_time,
            description="Groceries",
        )

        Transaction.objects.create(
            user=self.user,
            account=self.cash,
            type=Transaction.INCOME,
            category=self.income_category,
            subcategory=self.income_subcategory,
            amount=Decimal("500.00"),
            currency=self.eur,
            occurred_at=income_time,
            description="Salary",
        )

        Transfer.objects.create(
            user=self.user,
            from_account=self.cash,
            to_account=self.revolut,
            amount_from=Decimal("100.00"),
            amount_to=Decimal("100.00"),
            from_currency=self.eur,
            to_currency=self.eur,
            exchange_rate=Decimal("1.0000000000"),
            occurred_at=outgoing_transfer_time,
            description="To Revolut",
        )

        Transfer.objects.create(
            user=self.user,
            from_account=self.gbp_account,
            to_account=self.cash,
            amount_from=Decimal("100.00"),
            amount_to=Decimal("116.80"),
            from_currency=self.gbp,
            to_currency=self.eur,
            exchange_rate=Decimal("1.1680000000"),
            occurred_at=incoming_transfer_time,
            description="GBP to EUR",
        )

        history = get_account_history(
            user=self.user,
            account_id=self.cash.pk,
        )

        self.assertEqual(
            len(history),
            4,
        )

        self.assertEqual(
            [item["kind"] for item in history],
            [
                "transfer-in",
                "transfer-out",
                "income",
                "expense",
            ],
        )

        self.assertEqual(
            history[0]["amount"],
            Decimal("116.80"),
        )

        self.assertEqual(
            history[1]["amount"],
            Decimal("-100.00"),
        )

        self.assertEqual(
            history[2]["amount"],
            Decimal("500.00"),
        )

        self.assertEqual(
            history[3]["amount"],
            Decimal("-50.00"),
        )

        self.assertEqual(
            history[0]["transfer_account"],
            self.gbp_account,
        )

        self.assertEqual(
            history[1]["transfer_account"],
            self.revolut,
        )

    def test_history_does_not_include_another_users_data(self):
        other_account = Account.objects.create(
            user=self.other_user,
            name="Other Cash",
            currency=self.eur,
            opening_balance=Decimal("500.00"),
            current_balance=Decimal("500.00"),
        )

        Transaction.objects.create(
            user=self.other_user,
            account=other_account,
            type=Transaction.INCOME,
            category=self.income_category,
            subcategory=self.income_subcategory,
            amount=Decimal("999.00"),
            currency=self.eur,
            occurred_at=timezone.now(),
            description="Other user's income",
        )

        history = get_account_history(
            user=self.user,
            account_id=self.cash.pk,
        )

        self.assertEqual(
            history,
            [],
        )


class AccountReorderTests(TestCase):
    def setUp(self):
        self.currency = Currency.objects.get(code="EUR")

        self.user = User.objects.create_user(
            username="reorder_user",
            email="reorder@example.com",
            password="testpass123",
            base_currency=self.currency,
        )

        self.account_1 = Account.objects.create(
            user=self.user,
            name="Cash",
            currency=self.currency,
            opening_balance=100,
            current_balance=100,
            display_order=0,
        )

        self.account_2 = Account.objects.create(
            user=self.user,
            name="Bank",
            currency=self.currency,
            opening_balance=200,
            current_balance=200,
            display_order=1,
        )

        self.account_3 = Account.objects.create(
            user=self.user,
            name="Revolut",
            currency=self.currency,
            opening_balance=300,
            current_balance=300,
            display_order=2,
        )

    def test_reorder_accounts_updates_display_order(self):
        reorder_accounts(
            user=self.user,
            account_ids=[
                self.account_3.id,
                self.account_1.id,
                self.account_2.id,
            ],
        )

        self.account_1.refresh_from_db()
        self.account_2.refresh_from_db()
        self.account_3.refresh_from_db()

        self.assertEqual(self.account_3.display_order, 0)
        self.assertEqual(self.account_1.display_order, 1)
        self.assertEqual(self.account_2.display_order, 2)

    def test_reorder_accounts_rejects_foreign_account(self):
        other_user = User.objects.create_user(
            username="other_user",
            email="other@example.com",
            password="testpass123",
            base_currency=self.currency,
        )

        foreign_account = Account.objects.create(
            user=other_user,
            name="Foreign Account",
            currency=self.currency,
            opening_balance=500,
            current_balance=500,
            display_order=0,
        )

        with self.assertRaises(PermissionDenied):
            reorder_accounts(
                user=self.user,
                account_ids=[
                    self.account_1.id,
                    self.account_2.id,
                    foreign_account.id,
                ],
            )

    def test_reorder_accounts_rejects_incomplete_account_list(self):
        with self.assertRaises(PermissionDenied):
            reorder_accounts(
                user=self.user,
                account_ids=[
                    self.account_1.id,
                    self.account_2.id,
                ],
            )