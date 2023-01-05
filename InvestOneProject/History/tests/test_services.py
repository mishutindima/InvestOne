from datetime import datetime
from os import listdir
from os.path import isfile, join

from django.contrib.auth.models import User
from django.test import TestCase
from InvestOne.settings import MEDIA_ROOT

from ..models import Bill, Currency, ImportBrockerDataLog, MoneyDeal
from ..services.calc_sum_data_service import CalcSumDataService

IMPORT_FILE_FIELD_UPLOAD_TO = "import_brocker_data_log/"
IMPORT_FILES_MASK = "!!TESTCASE_OPEN_REPORT_"


# Create your tests here.
class ImportOpenReportTestCase(TestCase):
    """Тест кейсы для проверки корректности работы с брокерскими отчетами Открытия Брокер: парсинг, расчет остатков"""

    @classmethod
    def setUpTestData(cls):
        """Подготовка окружения для прохождения теста: создание пользователя, счета, импорт всех необходимых отчетов для брокерского счета в Открытии"""
        # 1. Создаем пользователя и счет
        cls.user = User.objects.create_user(username="tester", email="qq@qq.ru")
        cls.bill = Bill.objects.create(brocker_name="Открытие", owner=cls.user)
        cls.import_brocker_data_logs = []

        # 2. Выполняем загрузку данных для этого счета
        for file_item in listdir(MEDIA_ROOT / IMPORT_FILE_FIELD_UPLOAD_TO):
            if isfile(join(MEDIA_ROOT / IMPORT_FILE_FIELD_UPLOAD_TO, file_item)) and file_item.startswith(
                IMPORT_FILES_MASK
            ):
                import_data_log = ImportBrockerDataLog(
                    bill=cls.bill, status_code=ImportBrockerDataLog.StatusCodeChoices.NOT_STARTED
                )
                import_data_log.file_or_content.name = IMPORT_FILE_FIELD_UPLOAD_TO + file_item
                import_data_log.save()
                cls.import_brocker_data_logs.append(import_data_log)

    def setUp(self):
        """Установки запускаются перед каждым тестом"""
        pass

    def test_money_balance_on_31122019(self):
        """Проверка корректности импорта и расчета баланса на конец 2019 года"""
        true_balance = [
            CalcSumDataService.MoneyBalance(currency=Currency.objects.get(code="RUB"), balance=61121.98),
            CalcSumDataService.MoneyBalance(currency=Currency.objects.get(code="USD"), balance=36.29),
        ].sort(key=lambda x: x.currency.code)

        calc_balance = CalcSumDataService.get_money_balance_on_date(
            rep_bill=self.bill, date_of_report=datetime(year=2019, month=12, day=31)
        ).sort(key=lambda x: x.currency.code)
        # Обязательно сравниваем отсортированные списки, иначе из-за другого порядка они могут отличаться
        self.assertEqual(true_balance, calc_balance)

    """ def test_sign_of_data(self):
        MoneyDeal.objects.filter()
        self.assertFalse(False) """
