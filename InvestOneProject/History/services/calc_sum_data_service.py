from ..models import Bill, Share, ShareDeal, Currency, MoneyDeal, TypeOfDealsChoices, CurrencyExchangeDeal
import datetime
import decimal
from dataclasses import dataclass
from django.db.models import Sum, F


class CalcSumDataService:
    @dataclass
    class ShareBalance:
        share: Share
        count: decimal

    # Цель метода - возвращать остатки акций на конкретную дату
    @staticmethod
    def get_shares_balance_on_date(rep_bill: Bill, date_of_report: datetime.date) -> list[ShareBalance]:
        # https://django.fun/ru/docs/django/4.1/topics/db/aggregation/
        share_balance_list = []
        for share_count in ShareDeal.objects.filter(bill=rep_bill, datetime__lte=date_of_report).values(
                'share').annotate(count_of_share=Sum('count')):
            share_balance_list.append(CalcSumDataService.ShareBalance(share=Share.objects.get(id=share_count['share']),
                                                                      count=share_count['count_of_share']))

        return share_balance_list

    @dataclass
    class MoneyBalance:
        currency: Currency
        balance: decimal

    # Цель метода - возвращать остаток всех денежных средств на конкретную дату
    @staticmethod
    def get_money_balance_on_date(rep_bill: Bill, date_of_report: datetime.date) -> list[MoneyBalance]:
        money_balance_list = []
        # Обрабатываем последовательно все возможные операции
        # 1. Обрабатываем операции с деньгами
        money_deal_filter = MoneyDeal.objects.filter(bill=rep_bill, datetime__lte=date_of_report,
                                                     type_of_deal__in=[TypeOfDealsChoices.DIVIDENT_PAYMENT,
                                                                       TypeOfDealsChoices.REFILL_MONEY,
                                                                       TypeOfDealsChoices.WITHDRAWAL_MONEY,
                                                                       TypeOfDealsChoices.BROKER_COMMISSION,
                                                                       TypeOfDealsChoices.TAX]).values(
            'currency').annotate(
            sum_of_deal=Sum('sum'),
            sum_of_commission=Sum('commission'),
            sum_of_tax=Sum('tax'))
        for item in money_deal_filter:
            money_balance_list.append(
                CalcSumDataService.MoneyBalance(currency=Currency.objects.get(code=item["currency"]),
                                                balance=(item["sum_of_deal"] or 0) + (item["sum_of_commission"] or 0) +
                                                        (item["sum_of_tax"] or 0)))

        # 2. Обрабатываем валютообменные операции
        currency_exchange_deal_filter = CurrencyExchangeDeal.objects.filter(bill=rep_bill,
                                                                            datetime__lte=date_of_report).values(
            'currency_from',
            'currency_to',
            'commission_currency').annotate(
            sum_of_currency_from=Sum('currency_from_sum'),
            sum_of_currency_to=Sum('currency_to_sum'),
            sum_of_commission=Sum('commission'))
        for item in currency_exchange_deal_filter:
            money_balance_currency_from = CalcSumDataService._get_or_create_money_balance(money_balance_list,
                                                                                          item['currency_from'])
            money_balance_currency_from.balance += item['sum_of_currency_from']

            money_balance_currency_to = CalcSumDataService._get_or_create_money_balance(money_balance_list,
                                                                                        item['currency_to'])
            money_balance_currency_to.balance += item['sum_of_currency_to']

            if item['sum_of_commission'] is not None and item['sum_of_commission'] != 0:
                money_balance_commission = CalcSumDataService._get_or_create_money_balance(money_balance_list,
                                                                                           item['commission_currency'])
                money_balance_commission.balance += item['sum_of_commission']

        # 3. Обрабатываем операции с акциями
        share_deal_filter = ShareDeal.objects.filter(bill=rep_bill, datetime__lte=date_of_report).values('currency',
                                                                                                         'commission_currency').annotate(
            sum_of_deal=Sum(F("price") * F("count")),
            sum_of_commission=Sum('commission'))
        for item in share_deal_filter:
            money_balance = CalcSumDataService._get_or_create_money_balance(money_balance_list, item['currency'])
            money_balance.balance += item['sum_of_deal']

            if item['currency'] == item['commission_currency']:
                money_balance.balance += item['sum_of_commission']
            else:
                commission_money_balance = CalcSumDataService._get_or_create_money_balance(money_balance_list,
                                                                                           item['commission_currency'])
                commission_money_balance.balance += item['sum_of_commission']

        return money_balance_list

    # Помощник при расчете остатков финансов на счете
    @staticmethod
    def _get_or_create_money_balance(money_balance_list: [], currency_code: str) -> MoneyBalance:
        money_balance = next(
            (x for x in money_balance_list if x.currency.code == currency_code), None)
        if money_balance is None:
            money_balance = CalcSumDataService.MoneyBalance(
                currency=Currency.objects.get(code=currency_code), balance=0)
            money_balance_list.append(money_balance)
        return money_balance
