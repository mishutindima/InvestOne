from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords
from simple_history import register
from django.contrib.auth.models import User

register(User)


# Create your models here.
class Share(models.Model):
    isin = models.CharField(max_length=50)
    code = models.CharField(max_length=20)
    company_name = models.CharField(max_length=100)
    exchange_name = models.CharField(max_length=20)
    history = HistoricalRecords()
    def __str__(self):
        return self.code

class Bill(models.Model):
    brocker_name = models.CharField(max_length=20)
    bill_name = models.CharField(max_length=20)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    history = HistoricalRecords()
    def __str__(self):
        return self.brocker_name +" - " + self.bill_name

class Currency(models.Model):
    code = models.CharField(max_length=7, primary_key=True)
    name = models.CharField(max_length=20)
    history = HistoricalRecords()
    class Meta:
        verbose_name_plural = "Currencies"

    def __str__(self):
        return self.code

class BrockerPeriodicCommissions(models.Model):
    name = models.CharField(max_length=50)
    period_start = models.DateField()
    period_end = models.DateField(null=True)
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT)
    history = HistoricalRecords()

class TypeOfDeals(models.TextChoices):
    BUYING_SHARES = 'BUY_SR', 'Покупка акций'
    SALE_OF_SHARES = 'SL_SR', 'Продажа акций'
    DIVIDENT_PAYMENT = 'DIV', 'Выплата дивидендов/купонов'
    BUYING_BOND = 'BUY_BND', 'Покупка облигаций'
    SALE_OF_BOND = 'SL_BND', 'Продажа облигаций'
    REFILL_MONEY = 'RFL_MN', 'Внесение денег на счет'
    WITHDRAWAL_MONEY = 'WD_MN', 'Вывод денег со счета'
    BROKER_COMMISSION = 'BRK_CM', 'Брокерская комиссия'
    ERROR = 'ERR', 'Ошибка'

class MoneyDeal(models.Model):
    operation_number =models.CharField(max_length=30)
    type_of_deal = models.CharField(max_length=10,
                                    choices=TypeOfDeals.choices)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    share_by_divident = models.ForeignKey(Share, on_delete=models.PROTECT)
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT)
    datetime = models.DateTimeField()
    sum = models.DecimalField(max_digits=15, decimal_places=2)
    commission = models.DecimalField(max_digits=15, decimal_places=2)
    tax = models.DecimalField(max_digits=15, decimal_places=2)
    brocker_periodic_commissions = models.ForeignKey(BrockerPeriodicCommissions, on_delete=models.PROTECT, null=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.type_of_deal + self.currency

class ShareDeal(models.Model):
    operation_number = models.CharField(max_length=30)
    type_of_deal = models.CharField(max_length=10,
                                    choices=TypeOfDeals.choices)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT)
    datetime = models.DateTimeField()
    share = models.ForeignKey(Share, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=15, decimal_places=5)
    count = models.DecimalField(max_digits=15, decimal_places=2)
    commission = models.DecimalField(max_digits=15, decimal_places=2)
    history = HistoricalRecords()

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
    history = HistoricalRecords()

class InvestRecommendationAuthor(models.Model):
    name = models.CharField(max_length=50)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    history = HistoricalRecords()

class InvestRecommendation(models.Model):
    datetime = models.DateTimeField()
    author = models.ForeignKey(InvestRecommendationAuthor, on_delete=models.PROTECT)
    share = models.ForeignKey(Share, on_delete=models.PROTECT)
    share_deal = models.ForeignKey(ShareDeal, on_delete=models.PROTECT, null=True)
    money_deal = models.ForeignKey(MoneyDeal, on_delete=models.PROTECT, null=True)
    text = models.TextField()
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    history = HistoricalRecords()
