from django import forms
from django.contrib.auth.password_validation import validate_password

from apps.core.models import Currency
from apps.users.models import Profile, User


class RegistrationForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Username",
    )

    email = forms.EmailField(
        label="Email",
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
    )

    confirm_password = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
    )

    date_of_birth = forms.DateField(
        label="Date of birth",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"},
        ),
    )

    country = forms.CharField(
        max_length=100,
        label="Country",
    )

    profile_picture = forms.ImageField(
        label="Profile picture",
        required=False,
    )

    def clean_username(self):
        username = self.cleaned_data["username"]

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "A user with this username already exists."
            )

        return username

    def clean_email(self):
        email = self.cleaned_data["email"]

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "A user with this email already exists."
            )

        return email

    def clean_password(self):
        password = self.cleaned_data["password"]

        validate_password(password)

        return password

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if (
            password
            and confirm_password
            and password != confirm_password
        ):
            raise forms.ValidationError(
                "Passwords do not match."
            )

        return cleaned_data


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Username",
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
    )


class TwoFactorForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        label="Verification code",
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "maxlength": "6",
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data["code"]

        if not code.isdigit():
            raise forms.ValidationError(
                "The verification code must contain only digits."
            )

        return code


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "profile_picture",
            "date_of_birth",
            "country",
        ]

        widgets = {
            "date_of_birth": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
        }

    def clean_country(self):
        country = self.cleaned_data["country"].strip()

        if not country:
            raise forms.ValidationError(
                "Country cannot be empty."
            )

        return country


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "base_currency",
            "language",
            "two_fa_enabled",
        ]

        labels = {
            "base_currency": "Base currency",
            "language": "Language",
            "two_fa_enabled": "Two-factor authentication",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["base_currency"].queryset = (
            Currency.objects.filter(
                code__in=["EUR", "GBP", "USD"]
            ).order_by("code")
        )