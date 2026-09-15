from django.db import migrations


def create_currencies(apps, schema_editor):
    Currency = apps.get_model("core", "Currency")

    Currency.objects.bulk_create(
        [
            Currency(
                code="EUR",
                name="Euro",
                symbol="€",
            ),
            Currency(
                code="GBP",
                name="British Pound",
                symbol="£",
            ),
            Currency(
                code="USD",
                name="US Dollar",
                symbol="$",
            ),
        ]
    )


def remove_currencies(apps, schema_editor):
    Currency = apps.get_model("core", "Currency")

    Currency.objects.filter(
        code__in=["EUR", "GBP", "USD"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_currencies,
            remove_currencies,
        ),
    ]