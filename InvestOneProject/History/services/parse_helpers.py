from ..models import Currency, CurrencyAlternativeName


def get_currency_by_code(code: str) -> Currency:
    try:
        lower_code = code.strip().lower()
        return Currency.objects.get(code__iexact=lower_code)
    except Currency.DoesNotExist:
        currency_codes = CurrencyAlternativeName.objects.filter(alt_code__iexact=lower_code)
        if len(currency_codes) == 1:
            return currency_codes[0].code
        elif len(currency_codes) == 0:
            raise Exception('Not found Currency for code={}'.format(lower_code))
        else:
            raise Exception('Found several Currencies for code={}'.format(lower_code))
