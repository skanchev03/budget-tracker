from django import forms
from django.db.models import Q

from apps.accounts.models import Account
from apps.categories.models import Category, Subcategory
from apps.transactions.models import Transaction, Transfer


class CategorySelect(forms.Select):
    """
    Select widget that exposes the category type to JavaScript.
    """

    def create_option(
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None,
    ):
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex,
            attrs,
        )

        if hasattr(value, "instance") and value.instance is not None:
            option["attrs"]["data-type"] = value.instance.type

        return option


class TransactionForm(forms.Form):
    """
    Form for creating and editing Expense/Income transactions.
    """

    type = forms.ChoiceField(
        choices=Transaction.TYPE_CHOICES,
        label="Type",
    )

    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        label="Account",
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        label="Category",
        widget=CategorySelect(),
    )

    subcategory = forms.ModelChoiceField(
        queryset=Subcategory.objects.none(),
        label="Subcategory",
    )

    amount = forms.DecimalField(
        max_digits=19,
        decimal_places=4,
        min_value=0.0001,
        label="Amount",
    )

    occurred_at = forms.DateTimeField(
        label="Date and time",
        input_formats=[
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M",
        ],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={
                "type": "datetime-local",
            },
        ),
    )

    person = forms.CharField(
        max_length=150,
        required=False,
        label="Person",
    )

    description = forms.CharField(
        required=False,
        label="Comment",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
            }
        ),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        # ---------------------------------------------------------
        # Accounts
        # ---------------------------------------------------------

        self.fields["account"].queryset = (
            Account.objects
            .filter(
                user=user,
                is_active=True,
            )
            .select_related("currency")
            .order_by("display_order", "name")
        )

        # ---------------------------------------------------------
        # Categories
        # ---------------------------------------------------------

        self.fields["category"].queryset = (
            Category.objects
            .filter(
                Q(is_default=True)
                | Q(created_by=user)
            )
            .order_by("type", "name")
        )

        # ---------------------------------------------------------
        # Subcategories
        # ---------------------------------------------------------

        self.fields["subcategory"].queryset = (
            Subcategory.objects
            .filter(
                Q(is_default=True)
                | Q(created_by=user)
            )
            .select_related("category")
            .order_by("category__name", "name")
        )

    def clean_amount(self):
        amount = self.cleaned_data["amount"]

        if amount <= 0:
            raise forms.ValidationError(
                "Amount must be greater than zero."
            )

        return amount

    def clean(self):
        cleaned_data = super().clean()

        transaction_type = cleaned_data.get("type")
        account = cleaned_data.get("account")
        category = cleaned_data.get("category")
        subcategory = cleaned_data.get("subcategory")

        # ---------------------------------------------------------
        # Category type must match transaction type
        # ---------------------------------------------------------

        if transaction_type and category:
            if category.type != transaction_type:
                self.add_error(
                    "category",
                    "The category type must match "
                    "the transaction type.",
                )

        # ---------------------------------------------------------
        # Subcategory must belong to selected category
        # ---------------------------------------------------------

        if category and subcategory:
            if subcategory.category_id != category.id:
                self.add_error(
                    "subcategory",
                    "The subcategory must belong "
                    "to the selected category.",
                )

        # ---------------------------------------------------------
        # Category ownership
        # ---------------------------------------------------------

        if category:
            if (
                not category.is_default
                and category.created_by_id != self.user.id
            ):
                self.add_error(
                    "category",
                    "You can only use your own "
                    "custom categories.",
                )

        # ---------------------------------------------------------
        # Subcategory ownership
        # ---------------------------------------------------------

        if subcategory:
            if (
                not subcategory.is_default
                and subcategory.created_by_id != self.user.id
            ):
                self.add_error(
                    "subcategory",
                    "You can only use your own "
                    "custom subcategories.",
                )

        return cleaned_data


class TransferForm(forms.Form):
    """
    Form for creating and editing transfers between accounts.
    """

    from_account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        label="From account",
    )

    to_account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        label="To account",
    )

    amount_from = forms.DecimalField(
        max_digits=19,
        decimal_places=4,
        min_value=0.0001,
        label="Amount",
    )

    amount_to = forms.DecimalField(
        max_digits=19,
        decimal_places=4,
        min_value=0.0001,
        label="Received amount",
    )

    exchange_rate = forms.DecimalField(
        max_digits=20,
        decimal_places=10,
        min_value=0.0000000001,
        label="Exchange rate",
    )

    occurred_at = forms.DateTimeField(
        label="Date and time",
        input_formats=[
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M",
        ],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={
                "type": "datetime-local",
            },
        ),
    )

    description = forms.CharField(
        required=False,
        label="Comment",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
            }
        ),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        accounts = (
            Account.objects
            .filter(
                user=user,
                is_active=True,
            )
            .select_related("currency")
            .order_by("display_order", "name")
        )

        self.fields["from_account"].queryset = accounts
        self.fields["to_account"].queryset = accounts

    def clean_amount_from(self):
        amount = self.cleaned_data["amount_from"]

        if amount <= 0:
            raise forms.ValidationError(
                "Source amount must be greater than zero."
            )

        return amount

    def clean_amount_to(self):
        amount = self.cleaned_data["amount_to"]

        if amount <= 0:
            raise forms.ValidationError(
                "Destination amount must be greater than zero."
            )

        return amount

    def clean_exchange_rate(self):
        rate = self.cleaned_data["exchange_rate"]

        if rate <= 0:
            raise forms.ValidationError(
                "Exchange rate must be greater than zero."
            )

        return rate

    def clean(self):
        cleaned_data = super().clean()

        from_account = cleaned_data.get("from_account")
        to_account = cleaned_data.get("to_account")
        amount_from = cleaned_data.get("amount_from")
        amount_to = cleaned_data.get("amount_to")
        exchange_rate = cleaned_data.get("exchange_rate")

        # ---------------------------------------------------------
        # Source and destination must be different
        # ---------------------------------------------------------

        if (
            from_account
            and to_account
            and from_account.pk == to_account.pk
        ):
            self.add_error(
                "to_account",
                "Source and destination accounts "
                "must be different.",
            )

        # ---------------------------------------------------------
        # Destination amount must match exchange rate
        # ---------------------------------------------------------

        if (
            amount_from is not None
            and amount_to is not None
            and exchange_rate is not None
        ):
            expected_amount_to = (
                amount_from * exchange_rate
            )

            if abs(expected_amount_to - amount_to) > 0.0001:
                self.add_error(
                    "amount_to",
                    "The destination amount does not match "
                    "the source amount and exchange rate.",
                )

        return cleaned_data