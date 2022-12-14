from ..models import (
    Currency,
    Share,
    ImportBrockerDataLog,
    ShareDeal,
    TypeOfDealsChoices,
    CurrencyExchangeDeal,
    MoneyDeal,
    ShareAlternativeName,
    BoardNamesChoices,
    RepoDeal,
    DirectionOfOperation,
)
from .parse_helpers import get_currency_by_code
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import datetime
from itertools import groupby
import re


class ParseBrockerDataByOpen:
    # Цель класса - хранить в распарсенном виде данные по ЦБ, которые приходят из отчета
    @dataclass
    class BrockerReportShare:
        isin: str
        code: str
        name: str
        exchange_name: str

    import_brocker_data_log: ImportBrockerDataLog

    xml_report_root: ET.Element

    # Список ценных бумаг, которые упоминаются в отчете
    # список объектов типа BrockerReportShare
    xml_shares_mapping: list[BrockerReportShare]

    # TODO Мы никак не работаем с лотностью!!
    # TODO Подумать про безопасность парсинга XML, если будут пытаться взломать и удалить все
    def execute(self, import_brocker_data_log: ImportBrockerDataLog) -> None:
        self.import_brocker_data_log = import_brocker_data_log
        tree = ET.parse(import_brocker_data_log.file_or_content.file)
        self.xml_report_root = tree.getroot()

        if self.xml_report_root.attrib["portfolio"].strip().lower() == "единый брокерский счёт":
            self._general_parse_shares()
            self._general_parse_share_deals()
            self._general_parse_currency_exchange_deals()
            self._general_parse_nontrade_money_deals()
            self._general_parse_svop_deals()
            self._general_parse_money_deals()
        elif (
            self.xml_report_root.attrib["portfolio"].strip().lower()
            == "фондовый рынок санкт-петербургской биржи (фр спб)"
        ):
            self._spb_parse_share_deals()
            self._spb_parse_currency_exchange_deals()
            self._spb_parse_money_deals()
        elif self.xml_report_root.attrib["portfolio"].strip().lower() == "внебиржевой фондовый рынок (фр classica)":
            self._nontrade_parse_money_deals()
        else:
            raise Exception("Unknown portfolio type = {}".format(self.xml_report_root.attrib["portfolio"]))

    def _general_parse_shares(self):
        # 0. Получаем справочник ЦБ из отчета, чтобы использовать при парсинге сделок
        xml_shares = self.xml_report_root.findall("./spot_portfolio_security_params/item")
        self.xml_shares_mapping = list(
            map(
                lambda item: ParseBrockerDataByOpen.BrockerReportShare(
                    isin=item.attrib["isin"].strip(),
                    code=item.attrib["ticker"].strip(),
                    name=item.attrib["security_name"].strip(),
                    exchange_name=item.attrib["board_name"].strip(),
                ),
                xml_shares,
            )
        )

    # Заключенные в отчетном периоде сделки купли/продажи с ценными бумагами
    def _general_parse_share_deals(self):

        xml_share_deals = self.xml_report_root.findall(
            "./spot_main_deals_conclusion/item"
        )  # Бегаем по этому списку, т. к. в списке завершенных сделок нет времени заявки
        for item_xml in xml_share_deals:
            try:
                # Номер сделки, т. к. в рамках одной заявки может быть несколько сделок
                xml_share_deal_id = item_xml.attrib["deal_no"].strip()
                if xml_share_deal_id is None or xml_share_deal_id == "":
                    # не выполненная сделка
                    continue

                if (
                    ShareDeal.objects.filter(
                        operation_number=xml_share_deal_id,
                        bill=self.import_brocker_data_log.bill,
                        board_name=BoardNamesChoices.MOSCOW_BOARD,
                    ).exists()
                    is False
                ):

                    # Такой операции нет, значит нужно добавлять -> идем дальше по коду цикла
                    new_share_deal = ShareDeal(
                        operation_number=xml_share_deal_id,
                        bill=self.import_brocker_data_log.bill,
                        import_brocker_data_log=self.import_brocker_data_log,
                        board_name=BoardNamesChoices.MOSCOW_BOARD,
                    )

                    # Указываем ЦБ
                    # 1. Маппинг на ЦБ внутри отчета
                    shares_from_report = list(
                        filter(
                            lambda item: item.name == item_xml.attrib["security_name"].strip(), self.xml_shares_mapping
                        )
                    )
                    if len(shares_from_report) > 1:
                        raise "Найдено несколько подходящих ЦБ по названию. Просьба проверить содержимое отчета"
                    elif len(shares_from_report) == 0:
                        raise "Не найдено подходящих ЦБ по названию. Просьба проверить содержимое отчета"
                    # 2. Ищем ЦБ в справочнике системы
                    shares_from_model = Share.objects.filter(
                        isin=shares_from_report[0].isin
                    )  # используем именно filter, т к get кидает исключение когда не может получить запись, нам такое не надо.
                    if len(shares_from_model) > 1:
                        raise "Найдено несколько подходящих ЦБ по коду. Просьба проверить содержимое отчета"
                    elif len(shares_from_model) == 0:
                        # Регистрируем новую ЦБ в справочнике
                        share_model = Share(
                            isin=shares_from_report[0].isin,
                            code=shares_from_report[0].code,
                            name=shares_from_report[0].name,
                            exchange_name=shares_from_report[0].exchange_name,
                        )
                        share_model.save()
                        new_share_deal.share = share_model
                    else:
                        new_share_deal.share = shares_from_model[0]

                    if "buy_qnty" in item_xml.attrib and float(item_xml.attrib["buy_qnty"]) != 0:
                        new_share_deal.type_of_deal = TypeOfDealsChoices.BUYING_SHARES
                        new_share_deal.count_with_sign = float(item_xml.attrib["buy_qnty"])
                        new_share_deal.price_without_sign = float(item_xml.attrib["price"].strip())
                    elif "sell_qnty" in item_xml.attrib and float(item_xml.attrib["sell_qnty"]) != 0:
                        new_share_deal.type_of_deal = TypeOfDealsChoices.SALE_OF_SHARES
                        new_share_deal.count_with_sign = -float(item_xml.attrib["sell_qnty"])
                        new_share_deal.price_without_sign = float(item_xml.attrib["price"].strip())
                    else:
                        raise Exception(
                            "Doesn't find type operation buy or sell in deal id={}".format(xml_share_deal_id)
                        )

                    new_share_deal.currency = get_currency_by_code(item_xml.attrib["accounting_currency_code"])

                    new_share_deal.datetime = item_xml.attrib["conclusion_time"]
                    new_share_deal.commission = -float(item_xml.attrib["broker_commission"].strip())
                    new_share_deal.commission_currency = get_currency_by_code(
                        item_xml.attrib["broker_commission_currency_code"]
                    )

                    new_share_deal.save()
            except Exception as ex:
                raise Exception(
                    "Exception from parse xml_share_deals, text of xml:begin {} end".format(ET.tostring(item_xml))
                ) from ex

    # Расчёты по конверсионным сделкам, сделкам с драгоценными металлами
    def _general_parse_currency_exchange_deals(self):
        # Заключенные в отчётном периоде биржевые конверсионные сделки, сделки с драгоценными металлами
        # Не исполненные сделки!
        # Бегаем по этим записям, т к в исполненные в том числе попадают сделки репо, которые создают путаницу
        currency_exchange_deals_xml = self.xml_report_root.findall("./made_deal/item")
        for item_xml in currency_exchange_deals_xml:
            try:
                if "deal_number" not in item_xml.attrib:
                    continue  # не выполненные операции не обрабатываем

                xml_deal_number = item_xml.attrib["deal_number"].strip()
                if (
                    CurrencyExchangeDeal.objects.filter(
                        operation_number=xml_deal_number, bill=self.import_brocker_data_log.bill
                    ).exists()
                    is False
                ):
                    # Такой операции нет, значит нужно добавлять -> идем дальше по коду цикла
                    new_currency_exchange_deal = CurrencyExchangeDeal(
                        operation_number=xml_deal_number,
                        # Номер сделки, цель, чтобы она была уникальна!
                        bill=self.import_brocker_data_log.bill,
                        import_brocker_data_log=self.import_brocker_data_log,
                    )

                    new_currency_exchange_deal.datetime = datetime.datetime.combine(
                        datetime.datetime.strptime(item_xml.attrib["deal_date"], "%Y-%m-%dT%H:%M:%S").date(),
                        datetime.datetime.strptime(item_xml.attrib["deal_time"], "%Y-%m-%dT%H:%M:%S").time(),
                    )

                    executed_deal_xml = self.xml_report_root.find(
                        "./closed_deal/item/[@deal_number='{}']".format(xml_deal_number)
                    )
                    if executed_deal_xml is None:
                        raise Exception("Not find closed_deal for deal_number={}".format(xml_deal_number))

                    new_currency_exchange_deal.currency_from = get_currency_by_code(
                        executed_deal_xml.attrib["cocurrency_code"]
                    )
                    new_currency_exchange_deal.currency_to = get_currency_by_code(
                        executed_deal_xml.attrib["currency_code"]
                    )
                    # Обратить внимание на то как отображаются в отчете расходы, когда куплено несколько лотов или когда лот идет не по тысяче, а по 1 доллару
                    new_currency_exchange_deal.currency_from_sum = -float(
                        executed_deal_xml.attrib["volume"].lstrip("-")
                    )
                    new_currency_exchange_deal.currency_to_sum = executed_deal_xml.attrib["quantity"].lstrip("-")
                    new_currency_exchange_deal.commission = -float(item_xml.attrib["broker_comm"])
                    new_currency_exchange_deal.commission_currency = get_currency_by_code(
                        item_xml.attrib["broker_comm_currency_code"]
                    )
                    new_currency_exchange_deal.save()
            except Exception as ex:
                raise Exception(
                    "Exception from parse currency_exchange_deals_xml, text of xml:begin {} end".format(
                        ET.tostring(item_xml)
                    )
                ) from ex

    def _general_parse_nontrade_money_deals(self) -> None:
        money_nontrade_money_items_xml = self.xml_report_root.findall("./spot_nonstock_conversion_deals_executed/item")
        for item_xml in money_nontrade_money_items_xml:
            try:
                if item_xml.attrib["deal_type"] != "Конвертация":
                    raise Exception("Unknown type of operationtype={}".format(item_xml.attrib["deal_type"]))

                xml_deal_number = item_xml.attrib["trade_n"].strip()
                if (
                    CurrencyExchangeDeal.objects.filter(
                        operation_number=xml_deal_number, bill=self.import_brocker_data_log.bill
                    ).exists()
                    is False
                ):
                    # Такой операции нет, значит нужно добавлять -> идем дальше по коду цикла
                    new_currency_exchange_deal = CurrencyExchangeDeal(
                        operation_number=xml_deal_number,
                        bill=self.import_brocker_data_log.bill,
                        import_brocker_data_log=self.import_brocker_data_log,
                    )

                    new_currency_exchange_deal.datetime = datetime.datetime.strptime(
                        item_xml.attrib["conclusion_time"], "%Y-%m-%dT%H:%M:%S"
                    )
                    if item_xml.attrib["direction"] == "S":  # SELL
                        new_currency_exchange_deal.currency_from = get_currency_by_code(item_xml.attrib["currency_1"])
                        new_currency_exchange_deal.currency_to = get_currency_by_code(item_xml.attrib["currency_2"])
                        new_currency_exchange_deal.currency_from_sum = -float(item_xml.attrib["sum_1"])
                        new_currency_exchange_deal.currency_to_sum = float(item_xml.attrib["sum_2"])
                        new_currency_exchange_deal.commission = -float(item_xml.attrib["brokers_fee"])
                        new_currency_exchange_deal.commission_currency = get_currency_by_code(
                            item_xml.attrib["brokers_fee_currency"]
                        )
                    else:
                        raise Exception("Unknown type of direction".format(item_xml.attrib["direction"]))
                    new_currency_exchange_deal.save()
            except Exception as ex:
                raise Exception(
                    "Exception from parse spot_nonstock_conversion_deals_conclusion, text of xml:begin {} end".format(
                        ET.tostring(item_xml)
                    )
                ) from ex

    # Расчёты по сделкам СВОП
    # TODO Не парсим повторно сделки у которых на момент парсинга была 1-ая часть, но не было 2-ой. Получается такие сделки так и остаются полупустыми
    def _general_parse_svop_deals(self):
        # Заключенные в отчетном периоде биржевые сделки СВОП
        # Не исполненные сделки!
        svop_deals_xml = self.xml_report_root.findall("./made_swap_deal/item")
        for item_xml in svop_deals_xml:
            try:
                if "deal_number" not in item_xml.attrib:
                    continue  # не выполненные операции не обрабатываем
                xml_deal_number = item_xml.attrib["deal_number"].strip()
                if (
                    RepoDeal.objects.filter(
                        operation_number=xml_deal_number, bill=self.import_brocker_data_log.bill
                    ).exists()
                    is False
                ):
                    # Такой операции нет, значит нужно добавлять -> идем дальше по коду цикла
                    new_repo_deal = RepoDeal(
                        operation_number=xml_deal_number,
                        # Номер сделки, цель, чтобы она была уникальна!
                        bill=self.import_brocker_data_log.bill,
                        import_brocker_data_log=self.import_brocker_data_log,
                    )

                    new_repo_deal.datetime_first_part = item_xml.attrib["exec_date1"]
                    new_repo_deal.datetime_second_part = item_xml.attrib["exec_date2"]
                    if item_xml.attrib["exec_symbol"] == "S":
                        new_repo_deal.direction_first_part = DirectionOfOperation.SELL
                    elif item_xml.attrib["exec_symbol"] == "B":
                        new_repo_deal.direction_first_part = DirectionOfOperation.BUY
                    executed_deal_xml = self.xml_report_root.findall(
                        "./closed_deal/item/[@deal_number='{}']".format(xml_deal_number)
                    )
                    if executed_deal_xml is None:
                        raise Exception("Not find closed_deal for deal_number={}".format(xml_deal_number))
                    for item in executed_deal_xml:
                        if new_repo_deal.repo_currency is None:
                            new_repo_deal.repo_currency = get_currency_by_code(item.attrib["currency_code"])
                            new_repo_deal.related_currency = get_currency_by_code(item.attrib["cocurrency_code"])
                        if item.attrib["deal_symbol"] == "S":
                            new_repo_deal.count_without_sign = -float(item.attrib["quantity"])
                            new_repo_deal.price_first_part_with_sign = float(item.attrib["volume"])
                        elif item.attrib["deal_symbol"] == "B":
                            new_repo_deal.price_second_part_with_sign = float(item.attrib["volume"])

                    new_repo_deal.commission = -float(item_xml.attrib["broker_comm"])
                    new_repo_deal.commission_currency = get_currency_by_code(
                        item_xml.attrib["broker_comm_currency_code"]
                    )
                    new_repo_deal.save()
            except Exception as ex:
                raise Exception(
                    "Exception from parse svop_deals_xml, text of xml:begin {} end".format(ET.tostring(item_xml))
                ) from ex

    # 3. Прочие зачисления/списания денежных средств
    def _general_parse_money_deals(self):
        money_deal_items_xml = self.xml_report_root.findall("./unified_non_trade_money_operations/item")

        # !! У данных записей НЕТ уникального ID, поэтому прежде чем сохранить, проверяем есть ли уже подобные записи в БД
        # В отчете может быть несколько записей с одинаковыми параметрами, например 2 одинаковых пополнения на одинаковую сумму в один день, поэтому важно предварительно сгруппировать записи, чтобы не упустить похожие записи
        #  Полезные ссылки
        # https://pythonz.net/references/named/itertools.groupby/
        # https://stackoverflow.com/questions/51060140/itertools-group-by-multiple-keys
        def grouper(item):
            return (
                item.attrib["currency_code"],
                item.attrib["operation_date"],
                item.attrib["amount"],
                item.attrib["comment"],
            )

        # НЕ ПЫТАТЬСЯ переводить результат выполнения в LIST, тк это ломает сгруппированные записи. Т е key считается корректно, а group_items всегда пустой
        for key, group_items in groupby(sorted(money_deal_items_xml, key=grouper), key=grouper):
            try:
                group_iter = (i for i in group_items)
                len_of_group = sum(1 for _ in group_iter)

                # Проверяем до определения типа по тексту комментария, т. к. тип определяется уже по тексту
                saved_items = MoneyDeal.objects.filter(
                    bill=self.import_brocker_data_log.bill,
                    currency=get_currency_by_code(key[0]),
                    datetime=key[1],
                    sum=key[2],
                    comment=key[3],
                )
                if saved_items.count() >= len_of_group:
                    # Если кол-во записей в БД совпадает или больше кол-ва записей в отчете, то пропускаем эту запись
                    continue
                elif saved_items.count() == 0:
                    # создаем новую запись
                    new_money_deal = MoneyDeal()
                    new_money_deal.currency = get_currency_by_code(key[0])
                    new_money_deal.datetime = key[1]
                    # Переводим все в нижний регистр и удаляем двойные пробелы
                    type_of_operation = re.sub(" +", " ", key[3].lower())

                    # Онлайн редактор регулярных выражений, очень крутой - https://regex101.com/r/aGn8QC/2
                    # Полезная статья - https://habr.com/ru/post/349860/
                    if (
                        re.fullmatch("поставлены на торги средства клиента.+перевод на фс ммвб.+", type_of_operation)
                        or re.fullmatch("поставлены на торги средства клиента.+перевод с фс ммвб.+", type_of_operation)
                        or re.fullmatch("списаны средства клиента.+перевод на фс ммвб.+", type_of_operation)
                        or re.fullmatch("списаны средства клиента.+перевод на фр спб.+", type_of_operation)
                        or re.fullmatch("перевод денежных средств с клиента.+ портфель .+", type_of_operation)
                    ):
                        # Внутренняя запись о переводе денег между рынками, нам такое неинтересно
                        continue

                    elif re.fullmatch(".+комиссия брокера.+ за заключение сделок.+", type_of_operation) or re.fullmatch(
                        "вознаграждение брокера за заключение сделок конвертации дс .+", type_of_operation
                    ):
                        # Комиссии за операции с ЦБ и денежных средств уже учтены в операциях с ЦБ, повторно не импортируем
                        continue

                    elif re.fullmatch("поставлены на торги средства клиента.+", type_of_operation):
                        new_money_deal.type_of_deal = TypeOfDealsChoices.REFILL_MONEY

                    elif re.fullmatch("списаны средства клиента .+ для возврата на расчетный счет", type_of_operation):
                        new_money_deal.type_of_deal = TypeOfDealsChoices.WITHDRAWAL_MONEY
                        # 1. Ищем связанную строчку с комиссией за вывод
                        commission_items = list(
                            filter(
                                lambda x: x.attrib["operation_date"] == new_money_deal.datetime
                                and (
                                    re.sub(" +", " ", x.attrib["comment"].lower()).startswith(
                                        "комиссия за вывод средств клиента "
                                    )
                                    or re.sub(" +", " ", x.attrib["comment"].lower()).startswith(
                                        "вознаграждение брокера за обработку заявления на вывод безналичных денежных средств клиента "
                                    )
                                ),
                                money_deal_items_xml,
                            )
                        )
                        if len(commission_items) == 1:
                            new_money_deal.commission = commission_items[0].attrib["amount"]
                            new_money_deal.commission_currency = get_currency_by_code(
                                commission_items[0].attrib["currency_code"]
                            )
                        elif len(commission_items) > 1:
                            # Не обрабатываем кейсы, когда у нас несколько выводов за 1 день. Как минимум непонятно как их различать между собой. И не схлопнутся ли они
                            raise Exception("Length of commission_items".format(len(commission_items)))

                        # 2. Ищем связанную строчку с налогами
                        tax_items = list(
                            filter(
                                lambda x: x.attrib["operation_date"] == new_money_deal.datetime
                                and re.sub(" +", " ", x.attrib["comment"].lower()).startswith(
                                    "удержан налог на доход с клиента "
                                ),
                                money_deal_items_xml,
                            )
                        )
                        if len(tax_items) == 1:
                            new_money_deal.tax = tax_items[0].attrib["amount"]
                            new_money_deal.tax_currency = get_currency_by_code(tax_items[0].attrib["currency_code"])
                        elif len(tax_items) > 1:
                            # Не обрабатываем кейсы, когда у нас несколько выводов за 1 день. Как минимум непонятно как их различать между собой. И не схлопнутся ли они
                            raise Exception("Length of commission_items".format(len(tax_items)))

                    elif re.fullmatch("комиссия за вывод средств клиента .+", type_of_operation) or re.fullmatch(
                        "вознаграждение брокера за обработку заявления на вывод безналичных денежных средств клиента .+",
                        type_of_operation,
                    ):
                        # комиссии за вывод обрабатываем вместе с самим выводом, здесь игнорим запись
                        continue

                    elif re.fullmatch(
                        "комиссия за предоставление информации брокером по цб по месту хранения нко ао нрд.+",
                        type_of_operation,
                    ) or re.fullmatch(
                        "вознаграждение брокера за предоставление информации по движению и учету ценных бумаг.+",
                        type_of_operation,
                    ):
                        new_money_deal.type_of_deal = TypeOfDealsChoices.BROKER_COMMISSION

                    elif re.fullmatch("выплата дохода клиент .+ дивиденды.+", type_of_operation):
                        new_money_deal.type_of_deal = TypeOfDealsChoices.DIVIDEND_PAYMENT
                        self._general_take_info_about_dividend(new_money_deal, type_of_operation, money_deal_items_xml)

                    elif re.fullmatch("удержан налог на доход по дивидендам.+", type_of_operation):
                        # Пропускаем, т. к. налог учитываем сразу по строчке с дивидендом
                        continue
                    elif re.fullmatch("удержан налог на доход с клиента .+", type_of_operation):
                        # Пропускаем, т. к. налог за вывод денег считается сразу по факту вывода
                        continue

                    # Если тип не смогли определить - кидаем ошибку, чтобы сразу подсветить проблему, а не находить ее спустя какое-то время в данных
                    if new_money_deal.type_of_deal is None or new_money_deal.type_of_deal == "":
                        raise Exception("Unsupported type_of_deal for text='{}'".format(type_of_operation))

                    new_money_deal.sum = key[2]
                    new_money_deal.comment = key[3]
                    new_money_deal.bill = self.import_brocker_data_log.bill
                    new_money_deal.import_brocker_data_log = self.import_brocker_data_log
                    new_money_deal.save()
                    # если записей больше чем одна, то создаем дубли
                    if len_of_group > 1:
                        for item in range(len_of_group - 1):
                            new_money_deal.pk = None

                            new_money_deal.save()
                else:
                    # если сохранена уже одна запись, а должно быть больше - то дублируем найденные записи
                    for item in range(len_of_group - saved_items.count()):
                        saved_items[0].pk = None
                        saved_items[0].import_brocker_data_log = self.import_brocker_data_log
                        saved_items[0].save()
            except Exception as ex:
                raise Exception(
                    "Exception from parse money_deal_items_xml, text of key:begin {} end".format(key)
                ) from ex

    # Задача функции:
    # 1. Найти имя бумаги, по которой произошла выплата. Для российских бумаг - найти какой налог был уплачен
    # 2. По названию бумаги понять ее код
    def _general_take_info_about_dividend(
        self, new_money_deal: MoneyDeal, type_of_operation: str, money_deal_items_xml: list[ET.Element]
    ) -> None:
        # Шаг 1. Найти имя бумаги, по которой произошла выплата. Для российских бумаг - найти какой налог был уплачен
        # Первый тип написания - для российских бумаг
        name_of_share = re.search("(?<=дивиденды )(.+?)(?=-?\d* налог к удержанию)", type_of_operation)
        if name_of_share is not None and name_of_share.group() is not None:
            name_of_share = name_of_share.group()
            # Ищем подходящую строку с налогом
            # Почему здесь, а не в отдельном условии на уровне условий type_of_operation: (1)потому что важен порядок, на момент обработки строчки с налогом, записи с дивидендом может еще не быть;
            # (2) налог схлопываем в одну строчку с дивидендом
            tax_items = list(
                filter(
                    lambda x: re.sub(" +", " ", x.attrib["comment"].lower()).startswith(
                        "удержан налог на доход по дивидендам {}".format(name_of_share)
                    )
                    and x.attrib["operation_date"] == new_money_deal.datetime,
                    money_deal_items_xml,
                )
            )
            if len(tax_items) == 1:
                # Валюта у дивиденда и налога должна быть одна
                if tax_items[0].attrib["currency_code"] != new_money_deal.currency.code:
                    raise Exception("Different currencies for dividend and tax of dividend")
                new_money_deal.tax = tax_items[0].attrib["amount"]
                new_money_deal.tax_currency = get_currency_by_code(tax_items[0].attrib["currency_code"])
            elif len(tax_items) > 1:
                raise Exception("Length of tax_items for {} is {}".format(name_of_share, len(tax_items)))

        else:
            # Второй тип написания - для ГДР
            name_of_share = re.search("(?<=дивиденды )(.+?)(?=, комиссия платежного агента)", type_of_operation)
            if name_of_share is not None and name_of_share.group() is not None:
                name_of_share = name_of_share.group()
            else:
                raise Exception(
                    "Couldn't find name of share from string with dividends. type_of_operation={}".format(
                        type_of_operation
                    )
                )
            # Налог по таким записям не снимается, поэтому не ищем

        # Шаг 2. По названию бумаги понять ее код
        name_of_share = name_of_share.replace("-", " ")
        # Простое совпадение
        shares_by_div = list(filter(lambda x: x.name.lower() == name_of_share, self.xml_shares_mapping))
        if len(shares_by_div) == 1:
            new_money_deal.share_by_dividend = Share.objects.get(isin=shares_by_div[0].isin)
        else:
            name_of_share_without_type = re.search("(.+?)( апо| ао| аоо)", name_of_share)
            if name_of_share_without_type is not None and name_of_share_without_type.group() is not None:
                name_of_share = name_of_share_without_type.groups()[0]
                shares_by_div = list(filter(lambda x: x.name.lower() == name_of_share.strip(), self.xml_shares_mapping))
                if len(shares_by_div) == 1:
                    new_money_deal.share_by_dividend = Share.objects.get(isin=shares_by_div[0].isin)

            if new_money_deal.share_by_dividend is None:
                # Если не справился механизм алгоритмического поиска имени -> идем в словарь альтернативных названий
                try:
                    alt_share = ShareAlternativeName.objects.get(alt_name__iexact=name_of_share)
                    new_money_deal.share_by_dividend = alt_share.share
                except ShareAlternativeName.DoesNotExist:
                    raise Exception("Couldn't find share for name-{}".format(name_of_share))

    def _spb_parse_share_deals(self):

        xml_share_deals = self.xml_report_root.findall("./closed_deal/item")
        for item_xml in xml_share_deals:
            try:
                # Номер договора, т. к. в рамках одной заявки может быть несколько сделок
                xml_share_deal_id = item_xml.attrib["agreement"].strip()
                if xml_share_deal_id is None or xml_share_deal_id == "":
                    # не выполненная сделка, пропускаем
                    continue

                if (
                    ShareDeal.objects.filter(
                        operation_number=xml_share_deal_id,
                        bill=self.import_brocker_data_log.bill,
                        board_name=BoardNamesChoices.SPB_BOARD,
                    ).exists()
                    is False
                ):
                    # Такой операции нет, значит нужно добавлять -> идем дальше по коду цикла
                    new_share_deal = ShareDeal(
                        operation_number=xml_share_deal_id,
                        bill=self.import_brocker_data_log.bill,
                        import_brocker_data_log=self.import_brocker_data_log,
                        board_name=BoardNamesChoices.SPB_BOARD,
                    )
                    # Указываем ЦБ
                    try:
                        new_share_deal.share = Share.objects.get(isin=item_xml.attrib["isin"])
                    except Share.DoesNotExist:
                        new_share_deal.share = Share(
                            isin=item_xml.attrib["isin"],
                            code=item_xml.attrib["coderts"],
                            name=item_xml.attrib["issuername"],
                        )
                        new_share_deal.share.save()

                    if item_xml.attrib["operationtype"] == "Покупка":
                        new_share_deal.type_of_deal = TypeOfDealsChoices.BUYING_SHARES
                        new_share_deal.count_with_sign = float(item_xml.attrib["quantity"])
                        new_share_deal.price_without_sign = float(item_xml.attrib["price"].strip())
                    elif item_xml.attrib["operationtype"] == "Продажа":
                        new_share_deal.type_of_deal = TypeOfDealsChoices.SALE_OF_SHARES
                        new_share_deal.count_with_sign = float(item_xml.attrib["quantity"])
                        new_share_deal.price_without_sign = float(item_xml.attrib["price"].strip())
                    else:
                        raise Exception(
                            "Doesn't find type operation buy or sell in deal id={}".format(xml_share_deal_id)
                        )

                    new_share_deal.currency = get_currency_by_code(code=item_xml.attrib["paymentcurrency"])

                    new_share_deal.commission_currency = new_share_deal.currency
                    new_share_deal.datetime = datetime.datetime.combine(
                        datetime.datetime.strptime(item_xml.attrib["ticketdate"], "%Y-%m-%dT%H:%M:%S").date(),
                        datetime.datetime.strptime(item_xml.attrib["tickettime"], "%H:%M:%S").time(),
                    )
                    if "brokerage" in item_xml.attrib:
                        new_share_deal.commission = -float(item_xml.attrib["brokerage"].strip())
                    else:
                        new_share_deal.commission = 0
                    new_share_deal.save()
            except Exception as ex:
                raise Exception(
                    "Exception from parse xml_share_deals, text of xml:begin {} end".format(ET.tostring(item_xml))
                ) from ex

    # 2. Завершенные сделки по конвертации (в т.ч. Специальные сделки конвертации)
    def _spb_parse_currency_exchange_deals(self):
        currency_exchange_deals_xml = self.xml_report_root.findall("./spb_osl_deal_conv_closed/item")
        for item_xml in currency_exchange_deals_xml:
            try:
                if item_xml.attrib["operationtype"] != "Конвертация ДС":
                    raise Exception("Unknown type of operationtype={}".format(item_xml.attrib["operationtype"]))

                xml_deal_number = item_xml.attrib["dealnum"].strip()
                if (
                    CurrencyExchangeDeal.objects.filter(
                        operation_number=xml_deal_number, bill=self.import_brocker_data_log.bill
                    ).exists()
                    is False
                ):
                    # Такой операции нет, значит нужно добавлять -> идем дальше по коду цикла
                    new_currency_exchange_deal = CurrencyExchangeDeal(
                        operation_number=xml_deal_number,
                        bill=self.import_brocker_data_log.bill,
                        import_brocker_data_log=self.import_brocker_data_log,
                    )

                    new_currency_exchange_deal.datetime = datetime.datetime.combine(
                        datetime.datetime.strptime(item_xml.attrib["operationdate"], "%Y-%m-%dT%H:%M:%S").date(),
                        datetime.datetime.strptime(item_xml.attrib["dealtime"], "%H:%M:%S").time(),
                    )
                    if item_xml.attrib["direction"] == "Продажа":
                        new_currency_exchange_deal.currency_from = get_currency_by_code(
                            item_xml.attrib["destinationcurrency"]
                        )
                        new_currency_exchange_deal.currency_to = get_currency_by_code(item_xml.attrib["sourcecurrency"])
                        new_currency_exchange_deal.currency_from_sum = -float(item_xml.attrib["sumdestination"])
                        new_currency_exchange_deal.currency_to_sum = float(item_xml.attrib["sumsource"])
                        new_currency_exchange_deal.commission = 0
                        new_currency_exchange_deal.commission_currency = new_currency_exchange_deal.currency_from
                    else:
                        raise Exception("Unknown type of direction".format(item_xml.attrib["direction"]))

                    # КОМИССИИ НЕ ПАРСИМ, ТК НЕ БЫЛО ПРИМЕРА
                    new_currency_exchange_deal.save()
            except Exception as ex:
                raise Exception(
                    "Exception from parse spb_osl_deal_conv_closed, text of xml:begin {} end".format(
                        ET.tostring(item_xml)
                    )
                ) from ex

    def _spb_parse_money_deals(self) -> None:
        money_deal_items_xml = self.xml_report_root.findall("./nontrade_money_operation/item")

        for item_xml in money_deal_items_xml:
            try:
                # Номер договора, т. к. в рамках одной заявки может быть несколько сделок
                xml_money_deal_id = item_xml.attrib["transactionid"].strip()
                if xml_money_deal_id is None or xml_money_deal_id == "":
                    raise Exception("Couldn't find unique id in item={}".format(item_xml))

                if (
                    MoneyDeal.objects.filter(
                        operation_number=xml_money_deal_id, bill=self.import_brocker_data_log.bill
                    ).exists()
                    is False
                ):
                    # Такой операции нет, значит нужно добавлять -> идем дальше по коду цикла
                    new_money_deal = MoneyDeal(
                        operation_number=xml_money_deal_id,
                        bill=self.import_brocker_data_log.bill,
                        import_brocker_data_log=self.import_brocker_data_log,
                    )
                    match item_xml.attrib["analyticname"].strip():
                        case "Перевод между площадками/счетами ДС":
                            continue  # служебная запись, не сохраняем
                        case "Вознаграждение Брокера за организацию доступа к биржевым торгам с предоставлением информации клиентам, необходимой для совершения операций и сделок":
                            new_money_deal.type_of_deal = TypeOfDealsChoices.BROKER_COMMISSION
                        case "Комиссия Брокера за заключение сделок":
                            continue  # комиссия за заключение сделок учтена в сделках с акциями
                        case "Зачисление дивидендов":
                            new_money_deal.type_of_deal = TypeOfDealsChoices.DIVIDEND_PAYMENT
                            new_money_deal.share_by_dividend = self._spb_get_share_from_dividend(
                                item_xml.attrib["comment"].lower()
                            )
                        case "Списание ДС":
                            new_money_deal.type_of_deal = TypeOfDealsChoices.WITHDRAWAL_MONEY
                            comm_items = list(
                                filter(
                                    lambda x: x.attrib["analyticname"].strip()
                                    == "Вознаграждение Брокера за обработку заявления на вывод безналичных денежных средств"
                                    and x.attrib["operationdate"] == item_xml.attrib["operationdate"]
                                    and x.attrib["currencycode"] == item_xml.attrib["currencycode"],
                                    money_deal_items_xml,
                                )
                            )
                            if len(comm_items) == 1:
                                new_money_deal.commission = float(comm_items[0].attrib["amount"])
                                new_money_deal.commission_currency = get_currency_by_code(
                                    comm_items[0].attrib["currencycode"]
                                )
                            elif len(comm_items) > 1:
                                raise Exception(
                                    "Several commission items to WITHDRAWAL_MONEY by id={}".format(xml_money_deal_id)
                                )

                        case "Вознаграждение Брокера за обработку заявления на вывод безналичных денежных средств":
                            continue  # Запись пропускаем, т к комиссию учитываем в самой записи с выводом
                        case "Конвертация ДС":  # Валютно обменные операции
                            continue  # Пропускаем такие сделки, т к обрабатываем их в рамках парсинга валютообменных опперацй
                        case "Налог на доходы ФЛ /прибыль ЮЛ":
                            new_money_deal.type_of_deal = TypeOfDealsChoices.TAX
                        case _:
                            raise Exception("Unknown type of operation={}".format(item_xml.attrib["analyticname"]))

                    new_money_deal.datetime = item_xml.attrib["operationdate"]
                    new_money_deal.sum = float(item_xml.attrib["amount"])
                    new_money_deal.comment = item_xml.attrib["comment"]
                    new_money_deal.currency = get_currency_by_code(item_xml.attrib["currencycode"])
                    new_money_deal.save()
            except Exception as ex:
                raise Exception(
                    "Exception from parse nontrade_money_operation, text of key:begin {} end".format(
                        ET.tostring(item_xml)
                    )
                ) from ex

    def _spb_get_share_from_dividend(self, dividend_comment: str) -> Share:
        # 1. Вычленяем имя бумаги из строчки с дивидендами
        name_of_share_group = re.search("(?<=дивиденды <)(.+?)(?=-ао>)", dividend_comment)
        if name_of_share_group is None or name_of_share_group.group() == "":
            raise Exception("Unknown share by dividend={}".format(dividend_comment))
        name_of_share = name_of_share_group.group()
        try:
            # 2. Ищем по прямому соответствию
            return Share.objects.get(name__iexact=name_of_share)
        except Share.DoesNotExist:
            # 3. Пытаемся подбирать названия
            if name_of_share.endswith(" inc"):
                try:
                    return Share.objects.get(name__istartswith=name_of_share[0:-4])
                except Share.DoesNotExist:
                    pass
            # удаляем второстепенные знаки препинания
            try:
                name_of_share = name_of_share.replace(".", "").replace(",", "")
                return Share.objects.get(name__iexact=name_of_share)
            except Share.DoesNotExist:
                pass
            # 4. Если не нашли запись по прямому соответствию -> идем в словарь альтернативных названий
            try:
                return ShareAlternativeName.objects.get(alt_name__iexact=name_of_share).share
            except ShareAlternativeName.DoesNotExist:
                raise Exception("Couldn't find share for name-{}".format(name_of_share))

    def _nontrade_parse_money_deals(self) -> None:
        money_deal_items_xml = self.xml_report_root.findall("./nontrade_money_operation/item")

        for item_xml in money_deal_items_xml:
            try:
                xml_money_deal_id = item_xml.attrib["transaction_id"].strip()
                if xml_money_deal_id is None or xml_money_deal_id == "":
                    raise Exception("Coundn't find unique id in item={}".format(item_xml))

                if (
                    MoneyDeal.objects.filter(
                        operation_number=xml_money_deal_id, bill=self.import_brocker_data_log.bill
                    ).exists()
                    is False
                ):
                    # Такой операции нет, значит нужно добавлять -> идем дальше по коду цикла
                    new_money_deal = MoneyDeal(
                        operation_number=xml_money_deal_id,
                        bill=self.import_brocker_data_log.bill,
                        import_brocker_data_log=self.import_brocker_data_log,
                    )
                    match item_xml.attrib["analytic_name"].strip():
                        case "Перевод между площадками/счетами ДС":
                            continue  # служебная запись, не сохраняем
                        case "Налог на физ.лица (прошлый год)":
                            new_money_deal.type_of_deal = TypeOfDealsChoices.TAX
                        case _:
                            raise Exception("Unknown type of operation={}".format(item_xml.attrib["analyticname"]))

                    new_money_deal.datetime = item_xml.attrib["operation_date"]
                    new_money_deal.sum = float(item_xml.attrib["amount"])
                    new_money_deal.comment = item_xml.attrib["comment"]
                    new_money_deal.currency = get_currency_by_code(item_xml.attrib["currency_code"])
                    new_money_deal.save()
            except Exception as ex:
                raise Exception(
                    "Exception from parse nontrade_money_operation, text of key:begin {} end".format(
                        ET.tostring(item_xml)
                    )
                ) from ex
