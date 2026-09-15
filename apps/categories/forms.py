from django import forms
from django.db import models

from apps.categories.models import Category, Subcategory


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "emoji", "type"]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Category name",
                }
            ),
            "emoji": forms.TextInput(
                attrs={
                    "placeholder": "📁",
                    "maxlength": 10,
                }
            ),
            "type": forms.Select(),
        }

    def __init__(self, *args, user=None, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)

        self.user = user

        if instance is not None and instance.is_default:
            self.fields["name"].disabled = True
            self.fields["emoji"].disabled = True
            self.fields["type"].disabled = True

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError(
                "Category name cannot be empty."
            )

        return name

    def clean(self):
        cleaned_data = super().clean()

        if self.instance.pk and self.instance.is_default:
            raise forms.ValidationError(
                "Default categories cannot be modified."
            )

        return cleaned_data


class SubcategoryForm(forms.ModelForm):
    class Meta:
        model = Subcategory
        fields = ["category", "name"]

        widgets = {
            "category": forms.Select(),
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Subcategory name",
                }
            ),
        }

    def __init__(self, *args, user=None, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)

        self.user = user

        if user is not None:
            self.fields["category"].queryset = Category.objects.filter(
                models.Q(is_default=True)
                | models.Q(created_by=user)
            ).order_by("type", "name")

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError(
                "Subcategory name cannot be empty."
            )

        return name

    def clean(self):
        cleaned_data = super().clean()

        if self.instance.pk and self.instance.is_default:
            raise forms.ValidationError(
                "Default subcategories cannot be modified."
            )

        category = cleaned_data.get("category")

        if category is not None:
            if (
                not category.is_default
                and category.created_by != self.user
            ):
                raise forms.ValidationError(
                    "You cannot use another user's category."
                )

        return cleaned_data