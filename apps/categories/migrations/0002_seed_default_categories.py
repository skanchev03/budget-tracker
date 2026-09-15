from django.db import migrations


def seed_default_categories(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    Subcategory = apps.get_model("categories", "Subcategory")

    expense_categories = {
        "Food & Drinks": (
            "🍔",
            [
                "Groceries",
                "Restaurants",
                "Takeout",
                "Cafes",
                "Bars",
                "Alcohol",
            ],
        ),
        "Shopping": (
            "🛍️",
            [
                "Clothes",
                "Shoes",
                "Jewelry",
                "Accessories",
                "Beauty",
                "Kids",
                "Home",
                "Garden",
                "Tools",
                "Pets",
                "Animals",
                "Electronics",
                "Gifts",
                "Toys",
                "Tobacco",
            ],
        ),
        "Housing": (
            "🏠",
            [
                "Rent",
                "Mortgage",
                "Energy",
                "Water",
                "Utilities",
                "Services",
                "Maintenance",
                "Repairs",
                "Insurance",
            ],
        ),
        "Transportation": (
            "🚌",
            [
                "Bus",
                "Train",
                "Subway",
                "Taxi",
                "Flight",
            ],
        ),
        "Vehicle": (
            "🚗",
            [
                "Fuel",
                "Parking",
                "Maintenance",
                "Rental",
                "Insurance",
                "Leasing",
            ],
        ),
        "Entertainment": (
            "🎬",
            [
                "Events",
                "Hobbies",
                "Movies",
                "Music",
                "Nightlife",
                "Hotels",
                "Gambling",
            ],
        ),
        "Health": (
            "❤️",
            [
                "Health Care",
                "Wellness",
                "Pharmacy",
                "Doctor",
                "Dentist",
                "Tests",
            ],
        ),
        "Education": (
            "🎓",
            [
                "Courses",
                "Tuition",
                "Books",
                "Materials",
                "Training",
            ],
        ),
        "Electronics": (
            "📱",
            [
                "Phone",
                "Internet",
                "Games",
                "Software",
                "Subscriptions",
                "TV",
                "Services",
            ],
        ),
        "Financial": (
            "💰",
            [
                "Taxes",
                "Insurance",
                "Interest",
                "Fines",
                "Advisory",
                "Charges",
                "Fees",
            ],
        ),
    }

    income_categories = {
        "Income": (
            "💵",
            [
                "Wage",
                "Invoice",
                "Dividends",
                "Sale",
                "Rent",
                "Checks",
                "Coupons",
                "Gifts",
                "Gambling",
            ],
        ),
    }

    for category_name, (emoji, subcategories) in expense_categories.items():
        category = Category.objects.create(
            name=category_name,
            emoji=emoji,
            type="EXPENSE",
            is_default=True,
            created_by=None,
        )

        Subcategory.objects.bulk_create(
            [
                Subcategory(
                    category=category,
                    name=subcategory_name,
                    is_default=True,
                    created_by=None,
                )
                for subcategory_name in subcategories
            ]
        )

    for category_name, (emoji, subcategories) in income_categories.items():
        category = Category.objects.create(
            name=category_name,
            emoji=emoji,
            type="INCOME",
            is_default=True,
            created_by=None,
        )

        Subcategory.objects.bulk_create(
            [
                Subcategory(
                    category=category,
                    name=subcategory_name,
                    is_default=True,
                    created_by=None,
                )
                for subcategory_name in subcategories
            ]
        )


def reverse_seed_default_categories(apps, schema_editor):
    Category = apps.get_model("categories", "Category")

    Category.objects.filter(is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("categories", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            seed_default_categories,
            reverse_seed_default_categories,
        ),
    ]