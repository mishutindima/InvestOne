from ..models import Currency, Share, ImportBrockerDataLog, ShareDeal, TypeOfDealsChoices, CurrencyExchangeDeal, \
    MoneyDeal
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import datetime
import traceback
from itertools import groupby
import re


# Цель класса - парсить брокерский отчет или данные
class ParseBrockerDataService:
    # Цель класса - хранить в распарсенном виде данные по ЦБ, которые приходят из отчета
    @dataclass
    class BrockerReportShare:
        isin: str
        code: str
        name: str
        exchange_name: str
        currency_code: str

    def execute(self, import_brocker_data_log: ImportBrockerDataLog) -> None:

        try:
            import_brocker_data_log.status_code = ImportBrockerDataLog.StatusCodeChoices.STARTED
            import_brocker_data_log.save()

            if import_brocker_data_log.bill.brocker_name == "Открытие":
                self._parse_brocker_report_open(import_brocker_data_log)

            if import_brocker_data_log.bill.brocker_name == "ВТБ":
                self._parse_brocker_report_vtb(import_brocker_data_log)

            import_brocker_data_log.status_code = ImportBrockerDataLog.StatusCodeChoices.FINISHED_SUCCESS
            import_brocker_data_log.save()

        except Exception as ex:
            import_brocker_data_log.status_code = ImportBrockerDataLog.StatusCodeChoices.ERROR
            import_brocker_data_log.error_text = "{}\r\n{}".format(repr(ex), traceback.format_exc())
            import_brocker_data_log.save()

    @staticmethod
    def _parse_brocker_report_open(import_brocker_data_log: ImportBrockerDataLog) -> None:

        tree = ET.parse(import_brocker_data_log.file_or_content.file)
        root = tree.getroot()

        # 0. Получаем справочник ЦБ из отчета, чтобы использовать при парсинге сделок
        xml_shares = root.findall('./spot_portfolio_security_params/item')
        xml_shares_mapping = list(
            map(lambda item: ParseBrockerDataService.BrockerReportShare(isin=item.attrib["isin"].strip(),
                                                                        code=item.attrib["ticker"].strip(),
                                                                        name=item.attrib["security_name"].strip(),
                                                                        exchange_name=item.attrib["board_name"].strip(),
                                                                        currency_code=item.attrib[
                                                                            "nominal_curr"].strip()), xml_shares))

        # 1. Заключенные в отчетном периоде сделки купли/продажи с ценными бумагами
        xml_share_deals = root.findall('./spot_main_deals_conclusion/item')
        for xml_share_deal in xml_share_deals:
            xml_share_deal_id = xml_share_deal.attrib["request_no"].strip()  # Номер заявки
            if ShareDeal.objects.filter(operation_number=xml_share_deal_id,
                                        bill=import_brocker_data_log.bill).exists() is False:

                # Такой операции нет, значит нужно добавлять -> идем дальше по коду цикла
                new_share_deal = ShareDeal(operation_number=xml_share_deal_id,
                                           bill=import_brocker_data_log.bill,
                                           import_brocker_data_log=import_brocker_data_log)

                # Указываем ЦБ
                # 1. Маппинг на ЦБ внутри отчета
                shares_from_report = list(
                    filter(lambda item: item.name == xml_share_deal.attrib["security_name"].strip(),
                           xml_shares_mapping))
                if len(shares_from_report) > 1:
                    raise "Найдено несколько подходящих ЦБ по названию. Просьба проверить содержимое отчета"
                elif len(shares_from_report) == 0:
                    raise "Не найдено подходящих ЦБ по названию. Просьба проверить содержимое отчета"
                # 2. Ищем ЦБ в справочнике системы
                shares_from_model = Share.objects.filter(isin=shares_from_report[
                    0].isin)  # используем именно filter, т к get кидает исключение когда не может получить запись, нам такое не надо.
                if len(shares_from_model) > 1:
                    raise "Найдено несколько подходящих ЦБ по коду. Просьба проверить содержимое отчета"
                elif len(shares_from_model) == 0:
                    # Регистрируем новую ЦБ в справочнике
                    share_model = Share(isin=shares_from_report[0].isin,
                                        code=shares_from_report[0].code,
                                        name=shares_from_report[0].name,
                                        exchange_name=shares_from_report[0].exchange_name,
                                        currency=Currency.objects.get(code=shares_from_report[0].currency_code))
                    share_model.save()
                    new_share_deal.share = share_model
                else:
                    new_share_deal.share = shares_from_model[0]

                if xml_share_deal.attrib["buy_qnty"] is not None or float(xml_share_deal.attrib["buy_qnty"]) != 0:
                    new_share_deal.type_of_deal = TypeOfDealsChoices.BUYING_SHARES
                    new_share_deal.count = float(xml_share_deal.attrib["buy_qnty"])
                elif xml_share_deal.attrib["sell_qnty"] is not None or float(xml_share_deal.attrib["sell_qnty"]) != 0:
                    new_share_deal.type_of_deal = TypeOfDealsChoices.SALE_OF_SHARES
                    new_share_deal.count = float(xml_share_deal.attrib["sell_qnty"])

                new_share_deal.currency = new_share_deal.share.currency
                new_share_deal.datetime = xml_share_deal.attrib["conclusion_time"]
                new_share_deal.price = float(xml_share_deal.attrib["price"].strip())
                new_share_deal.commission = float(xml_share_deal.attrib["broker_commission"].strip())
                new_share_deal.commission_currency = Currency.objects.get(
                    code=xml_share_deal.attrib["broker_commission_currency_code"].strip())

                new_share_deal.save()

        # 2. Расчёты по конверсионным сделкам, сделкам с драгоценными металлами
        # Здесь бегаем именно по уже исполненным сделкам, т к по ним более понятно как рассчитать код валют которые менялись
        currency_exchange_deals_xml = root.findall('./closed_deal/item')
        for currency_exchange_deal_xml in currency_exchange_deals_xml:
            xml_order_number = currency_exchange_deal_xml.attrib["order_number"].strip()
            if CurrencyExchangeDeal.objects.filter(operation_number=xml_order_number,
                                                   bill=import_brocker_data_log.bill).exists() is False:
                # Такой операции нет, значит нужно добавлять -> идем дальше по коду цикла
                new_currency_exchange_deal = CurrencyExchangeDeal(operation_number=xml_order_number,
                                                                  # Номер заявки, цель, чтобы она была уникальна!
                                                                  bill=import_brocker_data_log.bill,
                                                                  import_brocker_data_log=import_brocker_data_log)

                new_currency_exchange_deal.datetime = datetime.datetime.combine(
                    datetime.datetime.strptime(currency_exchange_deal_xml.attrib["deal_date"],
                                               '%Y-%m-%dT%H:%M:%S').date(),
                    datetime.datetime.strptime(currency_exchange_deal_xml.attrib["deal_time"],
                                               '%Y-%m-%dT%H:%M:%S').time())

                new_currency_exchange_deal.currency_from = Currency.objects.get(
                    code=currency_exchange_deal_xml.attrib["cocurrency_code"])
                new_currency_exchange_deal.currency_to = Currency.objects.get(
                    code=currency_exchange_deal_xml.attrib["currency_code"])
                # Обратить внимание на то как отображаются в отчете расходы, когда куплено несколько лотов или когда лот идет не по тысяче, а по 1 доллару
                new_currency_exchange_deal.currency_from_sum = currency_exchange_deal_xml.attrib["volume"].lstrip("-")
                new_currency_exchange_deal.currency_to_sum = currency_exchange_deal_xml.attrib["quantity"].lstrip("-")

                commission_deal_item_xml = next(
                    filter(lambda item: item.attrib["order_number"] == new_currency_exchange_deal.operation_number,
                           root.findall('./made_deal/item')))
                new_currency_exchange_deal.commission = commission_deal_item_xml.attrib["broker_comm"]
                new_currency_exchange_deal.commission_currency = Currency.objects.get(
                    code=commission_deal_item_xml.attrib["broker_comm_currency_code"].strip())
                new_currency_exchange_deal.save()

        # 3. Прочие зачисления/списания денежных средств
        money_deal_items_xml = root.findall('./unified_non_trade_money_operations/item')

        # !! У данных записей НЕТ уникального ID, поэтому прежде чем сохранить, проверяем есть ли уже подобные записи в БД
        # В отчете может быть несколько записей с одинаковыми параметрами, например 2 одинаковых пополнения на одинаковую сумму в один день, поэтому важно предварительно сгруппировать записи, чтобы не упустить похожие записи
        #  Полезные ссылки
        # https://pythonz.net/references/named/itertools.groupby/
        # https://stackoverflow.com/questions/51060140/itertools-group-by-multiple-keys
        def grouper(item):
            return item.attrib['currency_code'], item.attrib["operation_date"], item.attrib["amount"], item.attrib[
                "comment"]

        # НЕ ПЫТАТЬСЯ переводить результат выполнения в LIST, тк это ломает сгруппированные записи. Т е key считается корректно, а group_items всегда пустой
        for key, group_items in groupby(sorted(money_deal_items_xml, key=grouper), key=grouper):
            iter = (i for i in group_items)
            len_of_group = sum(1 for _ in iter)

            # Проверяем до определения типа по тексту комментария, т к тип определяется уже по тексту
            saved_items = MoneyDeal.objects.filter(bill=import_brocker_data_log.bill,
                                                   currency=Currency.objects.get(code=key[0]),
                                                   datetime=key[1],
                                                   sum=key[2],
                                                   comment=key[3])
            if saved_items.count() >= len_of_group:
                # Если кол-во записей в БД совпадает или больше кол-ва записей в отчете, то пропускаем эту запись
                continue
            elif saved_items.count() == 0:
                new_money_deal = MoneyDeal()
                # Переводим все в нижний регистр и удаляем двойные пробелы
                type_of_operation = re.sub(" +", " ", key[3].lower())

                # Онлайн редактор регулярных выражений, очень крутой - https://regex101.com/r/aGn8QC/2
                # Полезная статья - https://habr.com/ru/post/349860/
                if (re.fullmatch("поставлены на торги средства клиента.+перевод на фс ммвб.+", type_of_operation) or
                        re.fullmatch("списаны средства клиента.+перевод на фс ммвб.+", type_of_operation) or
                        re.fullmatch("списаны средства клиента.+перевод на фр спб.+", type_of_operation) or
                        re.fullmatch("перевод денежных средств с клиента.+ портфель .+", type_of_operation)):
                    # Внутренняя запись о переводе денег между рынками, нам такое неинтересно
                    continue

                elif (
                        re.fullmatch(
                            ".+комиссия брокера.+ за заключение сделок.+на фондовый рынок московской биржи по счету.+",
                            type_of_operation)):
                    # Комиссии за операции с ЦБ уже учтены в операциях с ЦБ, повторно не импортируем
                    continue

                elif re.fullmatch("поставлены на торги средства клиента.+", type_of_operation):
                    new_money_deal.type_of_deal = TypeOfDealsChoices.REFILL_MONEY

                elif (re.fullmatch(
                        "комиссия за предоставление информации брокером по цб по месту хранения нко ао нрд.+",
                        type_of_operation) or
                      re.fullmatch(
                          "вознаграждение брокера за предоставление информации по движению и учету ценных бумаг.+",
                          type_of_operation)):
                    new_money_deal.type_of_deal = TypeOfDealsChoices.BROKER_COMMISSION

                elif re.fullmatch("выплата дохода клиент .+ дивиденды.+", type_of_operation):
                    new_money_deal.type_of_deal = TypeOfDealsChoices.DIVIDENT_PAYMENT
                    name_of_share = re.search("(?<=дивиденды )(.+?)(?=-\d+ налог к удержанию)",
                                              type_of_operation).group().lower()
                    shares_by_div = list(
                        filter(lambda x: x.name.lower() == name_of_share.replace("-", " "), xml_shares_mapping))
                    if len(shares_by_div) != 1:
                        # Если не нашли по полному совпадению пытаемся скорректировать строку и повторно поискать
                        # Ищем именно АО, т к на бирже могут быть только такие ЮЛ
                        if name_of_share.endswith("-ао"):
                            shares_by_div = list(
                                filter(lambda x: x.name.lower() == name_of_share.removesuffix("-ао").replace("-", " "),
                                       xml_shares_mapping))
                            if len(shares_by_div) != 1:
                                raise BaseException(
                                    "Error in search shares by div, count of items-{}".format(len(shares_by_div)))
                    new_money_deal.share_by_divident = Share.objects.get(isin=shares_by_div[0].isin)

                    # Ищем подходящую строку с налогом
                    # Почему здесь, а не в отдельном условии: (1)потому что важен порядок, на момент обработки строчки с налогом, записи с дивидендом может еще не быть; (2) налог схлопываем в одну строчку с дивидендом
                    tax_items = list(filter(lambda x: re.sub(" +", " ", x.attrib["comment"].lower()).startswith(
                        'удержан налог на доход по дивидендам {}'.format(name_of_share)),
                                            money_deal_items_xml))
                    if len(tax_items) > 1:
                        raise BaseException("Lenght of tax_items for {} is {}".format(name_of_share, len(tax_items)))
                    elif len(tax_items) == 1:
                        # Валюта у дивиденда и налога должна быть одна
                        if tax_items[0].attrib['currency_code'] != key[0]:
                            raise BaseException("Different currencies for dividend and tax of dividend")
                        new_money_deal.tax = tax_items[0].attrib['amount']

                elif re.fullmatch(".+ удержан налог на доход по дивидендам.+", type_of_operation):
                    # Пропускаем, т к налог учитываем сразу по строчке с дивидендом
                    continue

                new_money_deal.currency = Currency.objects.get(code=key[0])
                new_money_deal.datetime = key[1]
                new_money_deal.sum = key[2]
                new_money_deal.comment = key[3]
                new_money_deal.bill = import_brocker_data_log.bill
                new_money_deal.import_brocker_data_log = import_brocker_data_log
                new_money_deal.save()
                # если записей больше чем одна, то создаем дубли
                if len_of_group > 1:
                    for item in range(len_of_group - 1):
                        new_money_deal.pk = None

                        new_money_deal.save()
            else:
                for item in range(len_of_group - saved_items.count()):
                    saved_items[0].pk = None
                    saved_items[0].import_brocker_data_log = import_brocker_data_log
                    saved_items[0].save()

        return None

    def _parse_brocker_report_vtb(self, import_brocker_data_log: ImportBrockerDataLog) -> None:
        pass
