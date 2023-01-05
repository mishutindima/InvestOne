app_name = "History.apps.HistoryConfig"

# Цель метода - создать
def create_currencies(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.

    Currency = apps.get_model(app_name, "Currency")
    Currency.objects.create(code="RUB", name="Российский рубль")
    Currency.objects.create(code="USD", name="Доллар США")
    Currency.objects.create(code="EUR", name="Евро")

    CurrencyAlternativeName = apps.get_model(app_name, "CurrencyAlternativeName")
    CurrencyAlternativeName.objects.create(code="RUB", alt_code="RUR")
