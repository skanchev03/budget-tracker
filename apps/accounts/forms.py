from decimal import Decimal

from django import forms

from apps.accounts.models import Account
from apps.core.models import Currency


class CreateAccountForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        label="Account name",
    )

    emoji = forms.CharField(
        max_length=10,
        required=False,
        initial="💰",
        label="Emoji",
    )

    color = forms.CharField(
        max_length=7,
        required=False,
        initial="#3498DB",
        label="Color",
        widget=forms.TextInput(
            attrs={
                "type": "color",
            }
        ),
    )

    currency = forms.ModelChoiceField(
        queryset=Currency.objects.all(),
        label="Currency",
    )

    opening_balance = forms.DecimalField(
        max_digits=19,
        decimal_places=4,
        required=False,
        initial=None,
        label="Opening balance",
    )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError(
                "Account name cannot be empty."
            )

        return name

    def clean_emoji(self):
        emoji = self.cleaned_data.get("emoji")

        if not emoji:
            return "💰"

        return emoji.strip()

    def clean_color(self):
        color = self.cleaned_data.get("color")

        if not color:
            return "#3498DB"

        color = color.strip()

        if len(color) != 7 or not color.startswith("#"):
            raise forms.ValidationError(
                "Color must be a valid HEX color."
            )

        try:
            int(color[1:], 16)
        except ValueError:
            raise forms.ValidationError(
                "Color must be a valid HEX color."
            )

        return color.upper()

    def clean_opening_balance(self):
        opening_balance = self.cleaned_data.get(
            "opening_balance"
        )

        if opening_balance is None:
            return Decimal("0")

        return opening_balance


class UpdateAccountForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        label="Account name",
    )

    emoji = forms.CharField(
        max_length=10,
        required=False,
        label="Emoji",
    )

    color = forms.CharField(
        max_length=7,
        label="Color",
        widget=forms.TextInput(
            attrs={
                "type": "color",
            }
        ),
    )

    display_order = forms.IntegerField(
        required=False,
        initial=0,
        label="Display order",
    )

    is_active = forms.BooleanField(
        required=False,
        label="Active",
    )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError(
                "Account name cannot be empty."
            )

        return name

    def clean_emoji(self):
        emoji = self.cleaned_data.get("emoji")

        if not emoji:
            return "💰"

        return emoji.strip()

    def clean_color(self):
        color = self.cleaned_data.get("color")

        if not color:
            raise forms.ValidationError(
                "Color is required."
            )

        color = color.strip()

        if len(color) != 7 or not color.startswith("#"):
            raise forms.ValidationError(
                "Color must be a valid HEX color."
            )

        try:
            int(color[1:], 16)
        except ValueError:
            raise forms.ValidationError(
                "Color must be a valid HEX color."
            )

        return color.upper()