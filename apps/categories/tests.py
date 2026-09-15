from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from apps.categories.forms import CategoryForm, SubcategoryForm
from apps.categories.models import Category, Subcategory
from apps.categories.services import (
    create_category,
    create_subcategory,
    delete_category,
    delete_subcategory,
    get_categories_for_user,
    get_category_for_user,
    get_subcategories_for_user,
    get_subcategory_for_user,
    update_category,
    update_subcategory,
)
from apps.core.models import Currency
from apps.users.models import User


class CategoryTestBase(TestCase):
    def setUp(self):
        self.eur = Currency.objects.get(
            code="EUR"
        )

        self.user = User.objects.create_user(
            username="category_user",
            email="category@example.com",
            password="TestPassword123!",
            base_currency=self.eur,
        )

        self.other_user = User.objects.create_user(
            username="other_user",
            email="other@example.com",
            password="TestPassword123!",
            base_currency=self.eur,
        )

        self.default_expense_category = Category.objects.create(
            name="Food & Drinks",
            emoji="🍔",
            type=Category.EXPENSE,
            is_default=True,
            created_by=None,
        )

        self.default_income_category = Category.objects.create(
            name="Income",
            emoji="💰",
            type=Category.INCOME,
            is_default=True,
            created_by=None,
        )

        self.default_subcategory = Subcategory.objects.create(
            category=self.default_expense_category,
            name="Groceries",
            is_default=True,
            created_by=None,
        )

        self.custom_category = Category.objects.create(
            name="Gaming",
            emoji="🎮",
            type=Category.EXPENSE,
            is_default=False,
            created_by=self.user,
        )

        self.custom_subcategory = Subcategory.objects.create(
            category=self.custom_category,
            name="Steam",
            is_default=False,
            created_by=self.user,
        )

        self.other_category = Category.objects.create(
            name="Other User Category",
            emoji="📦",
            type=Category.EXPENSE,
            is_default=False,
            created_by=self.other_user,
        )

        self.other_subcategory = Subcategory.objects.create(
            category=self.other_category,
            name="Other User Subcategory",
            is_default=False,
            created_by=self.other_user,
        )


class CategoryServiceTests(CategoryTestBase):
    def test_get_categories_for_user_returns_default_and_own_categories(self):
        categories = get_categories_for_user(self.user)

        self.assertIn(
            self.default_expense_category,
            categories,
        )
        self.assertIn(
            self.default_income_category,
            categories,
        )
        self.assertIn(
            self.custom_category,
            categories,
        )
        self.assertNotIn(
            self.other_category,
            categories,
        )

    def test_get_category_for_user_returns_default_category(self):
        category = get_category_for_user(
            self.user,
            self.default_expense_category.id,
        )

        self.assertEqual(
            category,
            self.default_expense_category,
        )

    def test_get_category_for_user_returns_own_custom_category(self):
        category = get_category_for_user(
            self.user,
            self.custom_category.id,
        )

        self.assertEqual(
            category,
            self.custom_category,
        )

    def test_get_category_for_user_rejects_other_users_category(self):
        with self.assertRaises(PermissionDenied):
            get_category_for_user(
                self.user,
                self.other_category.id,
            )

    def test_create_category_creates_custom_category_for_user(self):
        category = create_category(
            self.user,
            name="Travel",
            emoji="✈️",
            category_type=Category.EXPENSE,
        )

        self.assertEqual(category.name, "Travel")
        self.assertEqual(category.emoji, "✈️")
        self.assertEqual(category.type, Category.EXPENSE)
        self.assertFalse(category.is_default)
        self.assertEqual(category.created_by, self.user)

    def test_update_own_custom_category(self):
        update_category(
            self.user,
            self.custom_category,
            name="Gaming & Games",
            emoji="🎮",
            category_type=Category.EXPENSE,
        )

        self.custom_category.refresh_from_db()

        self.assertEqual(
            self.custom_category.name,
            "Gaming & Games",
        )

    def test_cannot_update_default_category(self):
        with self.assertRaises(PermissionDenied):
            update_category(
                self.user,
                self.default_expense_category,
                name="Changed",
                emoji="❌",
                category_type=Category.EXPENSE,
            )

    def test_cannot_update_other_users_category(self):
        with self.assertRaises(PermissionDenied):
            update_category(
                self.user,
                self.other_category,
                name="Changed",
                emoji="❌",
                category_type=Category.EXPENSE,
            )

    def test_delete_own_custom_category(self):
        category_id = self.custom_category.id

        delete_category(
            self.user,
            self.custom_category,
        )

        self.assertFalse(
            Category.objects.filter(
                id=category_id,
            ).exists()
        )

    def test_deleting_custom_category_cascades_to_subcategories(self):
        subcategory_id = self.custom_subcategory.id

        delete_category(
            self.user,
            self.custom_category,
        )

        self.assertFalse(
            Subcategory.objects.filter(
                id=subcategory_id,
            ).exists()
        )

    def test_cannot_delete_default_category(self):
        with self.assertRaises(PermissionDenied):
            delete_category(
                self.user,
                self.default_expense_category,
            )

    def test_cannot_delete_other_users_category(self):
        with self.assertRaises(PermissionDenied):
            delete_category(
                self.user,
                self.other_category,
            )


class SubcategoryServiceTests(CategoryTestBase):
    def test_get_subcategories_for_user_returns_default_and_own(self):
        subcategories = get_subcategories_for_user(
            self.user
        )

        self.assertIn(
            self.default_subcategory,
            subcategories,
        )
        self.assertIn(
            self.custom_subcategory,
            subcategories,
        )
        self.assertNotIn(
            self.other_subcategory,
            subcategories,
        )

    def test_get_subcategory_for_user_returns_default(self):
        subcategory = get_subcategory_for_user(
            self.user,
            self.default_subcategory.id,
        )

        self.assertEqual(
            subcategory,
            self.default_subcategory,
        )

    def test_get_subcategory_for_user_returns_own_custom(self):
        subcategory = get_subcategory_for_user(
            self.user,
            self.custom_subcategory.id,
        )

        self.assertEqual(
            subcategory,
            self.custom_subcategory,
        )

    def test_get_subcategory_for_user_rejects_other_users_subcategory(self):
        with self.assertRaises(PermissionDenied):
            get_subcategory_for_user(
                self.user,
                self.other_subcategory.id,
            )

    def test_create_subcategory_for_default_category(self):
        subcategory = create_subcategory(
            self.user,
            category=self.default_expense_category,
            name="Meal Prep",
        )

        self.assertEqual(
            subcategory.name,
            "Meal Prep",
        )
        self.assertEqual(
            subcategory.category,
            self.default_expense_category,
        )
        self.assertFalse(
            subcategory.is_default
        )
        self.assertEqual(
            subcategory.created_by,
            self.user,
        )

    def test_create_subcategory_for_own_custom_category(self):
        subcategory = create_subcategory(
            self.user,
            category=self.custom_category,
            name="PlayStation",
        )

        self.assertEqual(
            subcategory.category,
            self.custom_category,
        )
        self.assertEqual(
            subcategory.created_by,
            self.user,
        )

    def test_cannot_create_subcategory_for_other_users_category(self):
        with self.assertRaises(PermissionDenied):
            create_subcategory(
                self.user,
                category=self.other_category,
                name="Forbidden",
            )

    def test_update_own_custom_subcategory(self):
        update_subcategory(
            self.user,
            self.custom_subcategory,
            category=self.custom_category,
            name="Steam Shop",
        )

        self.custom_subcategory.refresh_from_db()

        self.assertEqual(
            self.custom_subcategory.name,
            "Steam Shop",
        )

    def test_can_move_custom_subcategory_to_default_category(self):
        update_subcategory(
            self.user,
            self.custom_subcategory,
            category=self.default_expense_category,
            name="Steam",
        )

        self.custom_subcategory.refresh_from_db()

        self.assertEqual(
            self.custom_subcategory.category,
            self.default_expense_category,
        )

    def test_cannot_update_default_subcategory(self):
        with self.assertRaises(PermissionDenied):
            update_subcategory(
                self.user,
                self.default_subcategory,
                category=self.default_expense_category,
                name="Changed",
            )

    def test_cannot_update_other_users_subcategory(self):
        with self.assertRaises(PermissionDenied):
            update_subcategory(
                self.user,
                self.other_subcategory,
                category=self.other_category,
                name="Changed",
            )

    def test_cannot_move_subcategory_to_other_users_category(self):
        with self.assertRaises(PermissionDenied):
            update_subcategory(
                self.user,
                self.custom_subcategory,
                category=self.other_category,
                name="Steam",
            )

    def test_delete_own_custom_subcategory(self):
        subcategory_id = self.custom_subcategory.id

        delete_subcategory(
            self.user,
            self.custom_subcategory,
        )

        self.assertFalse(
            Subcategory.objects.filter(
                id=subcategory_id,
            ).exists()
        )

    def test_cannot_delete_default_subcategory(self):
        with self.assertRaises(PermissionDenied):
            delete_subcategory(
                self.user,
                self.default_subcategory,
            )

    def test_cannot_delete_other_users_subcategory(self):
        with self.assertRaises(PermissionDenied):
            delete_subcategory(
                self.user,
                self.other_subcategory,
            )


class CategoryFormTests(CategoryTestBase):
    def test_category_form_accepts_valid_data(self):
        form = CategoryForm(
            data={
                "name": "Travel",
                "emoji": "✈️",
                "type": Category.EXPENSE,
            },
            user=self.user,
        )

        self.assertTrue(form.is_valid())

    def test_category_form_rejects_empty_name(self):
        form = CategoryForm(
            data={
                "name": "   ",
                "emoji": "✈️",
                "type": Category.EXPENSE,
            },
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "name",
            form.errors,
        )

    def test_default_category_cannot_be_modified_through_form(self):
        form = CategoryForm(
            data={
                "name": self.default_expense_category.name,
                "emoji": self.default_expense_category.emoji,
                "type": self.default_expense_category.type,
            },
            user=self.user,
            instance=self.default_expense_category,
        )

        self.assertFalse(form.is_valid())


class SubcategoryFormTests(CategoryTestBase):
    def test_subcategory_form_accepts_default_category(self):
        form = SubcategoryForm(
            data={
                "category": self.default_expense_category.id,
                "name": "Meal Prep",
            },
            user=self.user,
        )

        self.assertTrue(form.is_valid())

    def test_subcategory_form_accepts_own_custom_category(self):
        form = SubcategoryForm(
            data={
                "category": self.custom_category.id,
                "name": "PlayStation",
            },
            user=self.user,
        )

        self.assertTrue(form.is_valid())

    def test_subcategory_form_does_not_offer_other_users_category(self):
        form = SubcategoryForm(
            user=self.user,
        )

        self.assertNotIn(
            self.other_category,
            form.fields["category"].queryset,
        )

    def test_subcategory_form_rejects_empty_name(self):
        form = SubcategoryForm(
            data={
                "category": self.custom_category.id,
                "name": "   ",
            },
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "name",
            form.errors,
        )

    def test_default_subcategory_cannot_be_modified_through_form(self):
        form = SubcategoryForm(
            data={
                "category": self.default_expense_category.id,
                "name": self.default_subcategory.name,
            },
            user=self.user,
            instance=self.default_subcategory,
        )

        self.assertFalse(form.is_valid())


class CategoryViewTests(CategoryTestBase):
    def setUp(self):
        super().setUp()

        self.client.login(
            username="category_user",
            password="TestPassword123!",
        )

    def test_category_list_loads_successfully(self):
        response = self.client.get(
            reverse("categories:category_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "categories/category_list.html",
        )

    def test_category_list_contains_default_and_own_category(self):
        response = self.client.get(
            reverse("categories:category_list")
        )

        self.assertContains(
            response,
            "Food &amp; Drinks",
        )
        self.assertContains(
            response,
            "Gaming",
        )

    def test_category_list_does_not_contain_other_users_category(self):
        response = self.client.get(
            reverse("categories:category_list")
        )

        self.assertNotContains(
            response,
            "Other User Category",
        )

    def test_create_category_view(self):
        response = self.client.post(
            reverse("categories:category_create"),
            {
                "name": "Travel",
                "emoji": "✈️",
                "type": Category.EXPENSE,
            },
        )

        self.assertRedirects(
            response,
            reverse("categories:category_list"),
        )

        self.assertTrue(
            Category.objects.filter(
                name="Travel",
                created_by=self.user,
                is_default=False,
            ).exists()
        )

    def test_update_own_category_view(self):
        response = self.client.post(
            reverse(
                "categories:category_update",
                args=[self.custom_category.id],
            ),
            {
                "name": "Gaming & Games",
                "emoji": "🎮",
                "type": Category.EXPENSE,
            },
        )

        self.assertRedirects(
            response,
            reverse("categories:category_list"),
        )

        self.custom_category.refresh_from_db()

        self.assertEqual(
            self.custom_category.name,
            "Gaming & Games",
        )

    def test_delete_own_category_view(self):
        response = self.client.post(
            reverse(
                "categories:category_delete",
                args=[self.custom_category.id],
            )
        )

        self.assertRedirects(
            response,
            reverse("categories:category_list"),
        )

        self.assertFalse(
            Category.objects.filter(
                id=self.custom_category.id,
            ).exists()
        )


class SubcategoryViewTests(CategoryTestBase):
    def setUp(self):
        super().setUp()

        self.client.login(
            username="category_user",
            password="TestPassword123!",
        )

    def test_create_subcategory_view(self):
        response = self.client.post(
            reverse("categories:subcategory_create"),
            {
                "category": self.custom_category.id,
                "name": "PlayStation",
            },
        )

        self.assertRedirects(
            response,
            reverse("categories:category_list"),
        )

        self.assertTrue(
            Subcategory.objects.filter(
                name="PlayStation",
                category=self.custom_category,
                created_by=self.user,
            ).exists()
        )

    def test_update_own_subcategory_view(self):
        response = self.client.post(
            reverse(
                "categories:subcategory_update",
                args=[self.custom_subcategory.id],
            ),
            {
                "category": self.custom_category.id,
                "name": "Steam Shop",
            },
        )

        self.assertRedirects(
            response,
            reverse("categories:category_list"),
        )

        self.custom_subcategory.refresh_from_db()

        self.assertEqual(
            self.custom_subcategory.name,
            "Steam Shop",
        )

    def test_delete_own_subcategory_view(self):
        response = self.client.post(
            reverse(
                "categories:subcategory_delete",
                args=[self.custom_subcategory.id],
            )
        )

        self.assertRedirects(
            response,
            reverse("categories:category_list"),
        )

        self.assertFalse(
            Subcategory.objects.filter(
                id=self.custom_subcategory.id,
            ).exists()
        )


class CategoryAuthenticationTests(CategoryTestBase):
    def test_category_list_requires_login(self):
        response = self.client.get(
            reverse("categories:category_list")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_category_create_requires_login(self):
        response = self.client.get(
            reverse("categories:category_create")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_subcategory_create_requires_login(self):
        response = self.client.get(
            reverse("categories:subcategory_create")
        )

        self.assertEqual(
            response.status_code,
            302,
        )