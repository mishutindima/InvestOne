from ..models import Bill, Share, ShareDeal, Currency
import datetime
import decimal
from dataclasses import dataclass
from django.db.models import Sum


class CalcSumDataService:
    @dataclass
    class ShareBalance:
        share: Share
        count: decimal

    # Цель метода - возвращать остатки акций на конкретную дату
    @staticmethod
    def get_shares_balance_on_date(rep_bill: Bill, date_of_report: datetime.date) -> list[ShareBalance]:
        # https://django.fun/ru/docs/django/4.1/topics/db/aggregation/
        shares_balance = []
        for share_count in ShareDeal.objects.filter(bill=rep_bill, datetime__lte=date_of_report).values(
                'share').annotate(count_of_share=Sum('count')):
            shares_balance.append(CalcSumDataService.ShareBalance(share=Share.objects.get(id=share_count['share']),
                                                                  count=share_count['count_of_share']))

        return shares_balance

    @dataclass
    class MoneyBalance:
        currency: Currency
        balance: decimal

    # Цель метода - возвращать остаток всех денежных средств на конкретную дату
    @staticmethod
    def get_money_balance_on_date(rep_bill: Bill, date_of_report: datetime.date) -> list[MoneyBalance]:
        money_balance = []
        # Обрабатываем последовательно все возможные операции
        # 1. Поступления денежных средств

        return money_balance
