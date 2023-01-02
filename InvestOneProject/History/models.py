from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords
from simple_history import register
from django.contrib.auth.models import User
from datetime import datetime

# simple-history#
register(User)

# !!!!!!!!!!!!!!!!!!!!!ВАЖНО!!!!!!!!!!!!!!!!!!
# ВСЕ СУММЫ ДЕНЕГ И КОЛ_ВО СОХРАНЯЮТСЯ В БД С ТАКИМ ЗНАКОМ, КАК ОНИ ВЛИЯЮТ НА БАЛАНС, Т Е РАСХОДНЫЕ С МИНУСОМ, ПРИХОДНЫЕ С ПЛЮСОМ


# Create your models here.
# Валюта
class Currency(models.Model):
    code = models.CharField(max_length=7, primary_key=True)
    name = models.CharField(max_length=20)
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Currencies"

    def __str__(self):
        return "{} ({})".format(self.name, self.code)

class CurrencyAlternativeName(models.Model):
    code = models.ForeignKey(Currency, on_delete=models.PROTECT)
    alt_code = models.CharField(max_length=7, primary_key=True)

    def __str__(self):
        return "{} (alt_name: {})".format(self.code, self.alt_code)

# Ценная бумага
class Share(models.Model):
    # Акция не должна содержать валюту, т к может быть несколько размещений акций в разных валютах. Показательный пример: Яндекс. Валюты: RUB, USD, KZT
    # Номинальная стоимость акции Яндекса - 0,01 EUR, показывает долю 1 акции в установном капитале компании. Если просто - бесполезный для меня показатель
    isin = models.CharField(max_length=50)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    history = HistoricalRecords()

    def __str__(self):
        return "{} (code = {}, isin = {})".format(self.name, self.code, self.isin)


# Словарь альтернативных названий ЦБ, нужно для распознавания ЦБ в тексте
class ShareAlternativeName(models.Model):
    share = models.ForeignKey(Share, on_delete=models.PROTECT)
    alt_name = models.CharField(max_length=100, primary_key=True)

    def __str__(self):
        return self.share.name + ": " + self.alt_name


# Счет
class Bill(models.Model):
    brocker_name = models.CharField(max_length=30)
    bill_name = models.CharField(max_length=50)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return self.brocker_name + " - " + self.bill_name


# Лог загрузки брокерских отчетов
class ImportBrockerDataLog(models.Model):
    class StatusCodeChoices(models.IntegerChoices):
        NOT_STARTED = '0', 'Не начато'
        STARTED = '1', 'Начато'
        FINISHED_SUCCESS = '2', 'Завершено успешно'
        ERROR = '-1', 'Завершено с ошибкой'

    datetime = models.DateTimeField(default=datetime.now())
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT)
    file_or_content = models.FileField(upload_to='import_brocker_data_log/')
    status_code = models.IntegerField(default=0, choices=StatusCodeChoices.choices)
    error_text = models.TextField()


#  Справочник типов сделок
class TypeOfDealsChoices(models.TextChoices):
    BUYING_SHARES = 'BUYING_SHARES', 'Покупка акций'
    SALE_OF_SHARES = 'SALE_OF_SHARES', 'Продажа акций'
    DIVIDENT_PAYMENT = 'DIVIDENT_PAYMENT', 'Выплата дивидендов/купонов'
    BUYING_BOND = 'BUYING_BOND', 'Покупка облигаций'
    SALE_OF_BOND = 'SALE_OF_BOND', 'Продажа облигаций'
    REFILL_MONEY = 'REFILL_MONEY', 'Внесение денег на счет'
    WITHDRAWAL_MONEY = 'WITHDRAWAL_MONEY', 'Вывод денег со счета'
    BROKER_COMMISSION = 'BROKER_COMMISSION', 'Брокерская комиссия'
    TAX = 'TAX', 'Налоги'
    UNKNOWN_TYPE = 'UNKNOWN', 'Не распознанный тип'
    ERROR = 'ERROR', 'Ошибка'


# Сделки с деньгами
class MoneyDeal(models.Model):
    operation_number = models.CharField(max_length=30, blank=True, null=True)
    type_of_deal = models.CharField(max_length=20,
                                    choices=TypeOfDealsChoices.choices)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    share_by_divident = models.ForeignKey(Share, on_delete=models.PROTECT, blank=True,
                                          null=True)  # Выплата дивидендов по ЦБ
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT)
    datetime = models.DateTimeField()
    sum = models.DecimalField(max_digits=15, decimal_places=2)
    commission = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    commission_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='+', blank=True, null=True)
    tax = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tax_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='+', blank=True, null=True)
    comment = models.CharField(max_length=200, blank=True, null=True)
    import_brocker_data_log = models.ForeignKey(ImportBrockerDataLog, on_delete=models.CASCADE, blank=True, null=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.type_of_deal


class BoardNamesChoices(models.TextChoices):
    MOSCOW_BOARD = 'MOSCOW_BOARD', 'Московская биржа'
    SPB_BOARD = 'SPB_BOARD', 'Санкт-Петербургская биржа (ФР СПб)'

# Сделки с ценными бумагами
class ShareDeal(models.Model):
    operation_number = models.CharField(max_length=30)
    type_of_deal = models.CharField(max_length=20,
                                    choices=TypeOfDealsChoices.choices)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT)
    datetime = models.DateTimeField()
    share = models.ForeignKey(Share, on_delete=models.PROTECT)
    price_without_sign = models.DecimalField(max_digits=15, decimal_places=5)
    count_with_sign = models.DecimalField(max_digits=15, decimal_places=2)
    commission = models.DecimalField(max_digits=15, decimal_places=2)
    commission_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='+')
    import_brocker_data_log = models.ForeignKey(ImportBrockerDataLog, on_delete=models.CASCADE, blank=True, null=True)
    board_name = models.CharField(max_length=20, choices=BoardNamesChoices.choices)

    history = HistoricalRecords()

    def __str__(self):
        return "Счет:{}, Дата:{}, Операция:{}, ЦБ:{}".format(self.bill, self.datetime, self.type_of_deal,
                                                             self.share.name)


# Сделки обмена валют
class CurrencyExchangeDeal(models.Model):
    operation_number = models.CharField(max_length=30)
    datetime = models.DateTimeField()
    currency_from = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='+')
    currency_to = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='+')
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT)
    currency_from_sum = models.DecimalField(max_digits=15, decimal_places=2)
    currency_to_sum = models.DecimalField(max_digits=15, decimal_places=2)
    commission = models.DecimalField(max_digits=15, decimal_places=2)
    commission_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='+')
    import_brocker_data_log = models.ForeignKey(ImportBrockerDataLog, on_delete=models.CASCADE, blank=True, null=True)

    history = HistoricalRecords()


# Авторы инвестиционных рекомендаций
class InvestRecommendationAuthor(models.Model):
    name = models.CharField(max_length=50)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    history = HistoricalRecords()


# Инвестиционные рекомендации
class InvestRecommendation(models.Model):
    datetime = models.DateTimeField()
    author = models.ForeignKey(InvestRecommendationAuthor, on_delete=models.PROTECT)
    share = models.ForeignKey(Share, on_delete=models.PROTECT)
    share_deal = models.ForeignKey(ShareDeal, on_delete=models.PROTECT, null=True)
    money_deal = models.ForeignKey(MoneyDeal, on_delete=models.PROTECT, null=True)
    text = models.TextField()
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    history = HistoricalRecords()

class DirectionOfOperation(models.TextChoices):
    SELL = 'SELL', 'Продажа'
    BUY = 'BUY', 'Покупка'

# Сделки репо - единый класс как для валют, так и для ЦБ
# Логика: 1-ая часть - продается актив, получается выручка в виде связанной валюты;
# 2-ая часть - покупается данный актив, валюта тратится
class RepoDeal(models.Model):
    operation_number = models.CharField(max_length=30)
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT)
    datetime_first_part = models.DateTimeField()
    datetime_second_part = models.DateTimeField()
    direction_first_part = models.CharField(max_length=4, choices=DirectionOfOperation.choices)
    # Одно из этих полей должно быть заполнено
    repo_share = models.ForeignKey(Share, on_delete=models.PROTECT, null=True, related_name='+')
    repo_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, related_name='+')

    count_without_sign = models.DecimalField(max_digits=15, decimal_places=2)
    price_first_part_with_sign = models.DecimalField(max_digits=15, decimal_places=2)
    price_second_part_with_sign = models.DecimalField(max_digits=15, decimal_places=2)
    related_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='+')
    commission = models.DecimalField(max_digits=15, decimal_places=2)
    commission_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='+')
    import_brocker_data_log = models.ForeignKey(ImportBrockerDataLog, on_delete=models.CASCADE, blank=True, null=True)

    history = HistoricalRecords()

# Репо сделки с активами
