from ..models import Currency, Share, ImportBrockerDataLog, ShareDeal, TypeOfDealsChoices, CurrencyExchangeDeal, \
    MoneyDeal
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

    xml_shares_mapping: []

    # TODO Мы никак не работаем с лотностью!!
    # TODO Подумать про безопасность парсинга XML, если будут пытаться взломать и удалить все
    def execute(self, import_brocker_data_log: ImportBrockerDataLog) -> None:
        self.import_brocker_data_log = import_brocker_data_log
        tree = ET.parse(import_brocker_data_log.file_or_content.file)
        self.xml_report_root = tree.getroot()
        self._parse_shares()
        self._parse_share_deals()
        self._parse_currency_exchange_deals()
        self._parse_money_deals()

    def _parse_shares(self):
        # 0. Получаем справочник ЦБ из отчета, чтобы использовать при парсинге сделок
        xml_shares = self.xml_report_root.findall('./spot_portfolio_security_params/item')
        self.xml_shares_mapping = list(
            map(lambda item: ParseBrockerDataByOpen.BrockerReportShare(isin=item.attrib["isin"].strip(),
                                                                       code=item.attrib["ticker"].strip(),
                                                                       name=item.attrib["security_name"].strip(),
                                                                       exchange_name=item.attrib[
                                                                           "board_name"].strip()), xml_shares))

    # 1. Заключенные в отчетном периоде сделки купли/продажи с ценными бумагами
    def _parse_share_deals(self):

        xml_share_deals = self.xml_report_root.findall(
            './spot_main_deals_conclusion/item')  # Бегаем по этому списку, т. к. в списке завершенных сделок нет времени заявки
        for xml_share_deal in xml_share_deals:
            try:
                xml_share_deal_id = xml_share_deal.attrib[
                    "deal_no"].strip()  # Номер сделки, т. к. в рамках одной заявки может быть несколько сделок
                if xml_share_deal_id is None or xml_share_deal_id == "":
                    # не выполненная сделка
                    continue

                if ShareDeal.objects.filter(operation_number=xml_share_deal_id,
                                            bill=self.import_brocker_data_log.bill).exists() is False:

                    # Такой операции нет, значит нужно добавлять -> идем дальше по коду цикла
                    new_share_deal = ShareDeal(operation_number=xml_share_deal_id,
                                               bill=self.import_brocker_data_log.bill,
                                               import_brocker_data_log=self.import_brocker_data_log)

                    # Указываем ЦБ
                    # 1. Маппинг на ЦБ внутри отчета
                    shares_from_report = list(
                        filter(lambda item: item.name == xml_share_deal.attrib["security_name"].strip(),
                               self.xml_shares_mapping))
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
                                            exchange_name=shares_from_report[0].exchange_name)
                        share_model.save()
                        new_share_deal.share = share_model
                    else:
                        new_share_deal.share = shares_from_model[0]

                    if "buy_qnty" in xml_share_deal.attrib and float(xml_share_deal.attrib["buy_qnty"]) != 0:
                        new_share_deal.type_of_deal = TypeOfDealsChoices.BUYING_SHARES
                        new_share_deal.count = float(xml_share_deal.attrib["buy_qnty"])
                        new_share_deal.price = -float(xml_share_deal.attrib["price"].strip())
                    elif "sell_qnty" in xml_share_deal.attrib and float(xml_share_deal.attrib["sell_qnty"]) != 0:
                        new_share_deal.type_of_deal = TypeOfDealsChoices.SALE_OF_SHARES
                        new_share_deal.count = float(xml_share_deal.attrib["sell_qnty"])
                        new_share_deal.price = float(xml_share_deal.attrib["price"].strip())
                    else:
                        raise Exception(
                            "Doesn't find type operation buy or sell in deal id={}".format(xml_share_deal_id))

                    try:
                        new_share_deal.currency = Currency.objects.get(
                            code=xml_share_deal.attrib["accounting_currency_code"].strip())
                    except Currency.DoesNotExist:
                        raise Currency.DoesNotExist(
                            "DoesNotExist currency-{}".format(
                                xml_share_deal.attrib["accounting_currency_code"].strip()))

                    new_share_deal.datetime = xml_share_deal.attrib["conclusion_time"]
                    new_share_deal.commission = -float(xml_share_deal.attrib["broker_commission"].strip())
                    try:
                        new_share_deal.commission_currency = Currency.objects.get(
                            code=xml_share_deal.attrib["broker_commission_currency_code"].strip())
                    except Currency.DoesNotExist:
                        raise Currency.DoesNotExist("DoesNotExist currency-{}".format(
                            xml_share_deal.attrib["broker_commission_currency_code"].strip()))

                    new_share_deal.save()
            except Exception as ex:
                raise Exception(
                    "Exception from parse xml_share_deals, text of xml:begin {} end".format(xml_share_deal)) from ex

    # 2. Расчёты по конверсионным сделкам, сделкам с драгоценными металлами
    def _parse_currency_exchange_deals(self):
        # Здесь бегаем именно по уже исполненным сделкам, т. к. по ним более понятно как рассчитать код валют которые менялись
        currency_exchange_deals_xml = self.xml_report_root.findall('./closed_deal/item')
        for currency_exchange_deal_xml in currency_exchange_deals_xml:
            try:
                xml_order_number = currency_exchange_deal_xml.attrib["deal_number"].strip()
                if CurrencyExchangeDeal.objects.filter(operation_number=xml_order_number,
                                                       bill=self.import_brocker_data_log.bill).exists() is False:
                    # Такой операции нет, значит нужно добавлять -> идем дальше по коду цикла
                    new_currency_exchange_deal = CurrencyExchangeDeal(operation_number=xml_order_number,
                                                                      # Номер заявки, цель, чтобы она была уникальна!
                                                                      bill=self.import_brocker_data_log.bill,
                                                                      import_brocker_data_log=self.import_brocker_data_log)

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
                    new_currency_exchange_deal.currency_from_sum = -float(
                        currency_exchange_deal_xml.attrib["volume"].lstrip("-"))
                    new_currency_exchange_deal.currency_to_sum = currency_exchange_deal_xml.attrib["quantity"].lstrip(
                        "-")

                    commission_deal_item_xml = next(
                        filter(lambda item: item.attrib["order_number"] == currency_exchange_deal_xml.attrib[
                            "order_number"].strip(),
                               self.xml_report_root.findall('./made_deal/item')))
                    new_currency_exchange_deal.commission = -float(commission_deal_item_xml.attrib["broker_comm"])
                    new_currency_exchange_deal.commission_currency = Currency.objects.get(
                        code=commission_deal_item_xml.attrib["broker_comm_currency_code"].strip())
                    new_currency_exchange_deal.save()
            except Exception as ex:
                raise Exception("Exception from parse currency_exchange_deals_xml, text of xml:begin {} end".format(
                    currency_exchange_deal_xml)) from ex

    # 3. Прочие зачисления/списания денежных средств
    def _parse_money_deals(self):
        money_deal_items_xml = self.xml_report_root.findall('./unified_non_trade_money_operations/item')

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
            try:
                group_iter = (i for i in group_items)
                len_of_group = sum(1 for _ in group_iter)

                # Проверяем до определения типа по тексту комментария, т. к. тип определяется уже по тексту
                saved_items = MoneyDeal.objects.filter(bill=self.import_brocker_data_log.bill,
                                                       currency=Currency.objects.get(code=key[0]),
                                                       datetime=key[1],
                                                       sum=key[2],
                                                       comment=key[3])
                if saved_items.count() >= len_of_group:
                    # Если кол-во записей в БД совпадает или больше кол-ва записей в отчете, то пропускаем эту запись
                    continue
                elif saved_items.count() == 0:
                    # создаем новую запись
                    new_money_deal = MoneyDeal()
                    # Переводим все в нижний регистр и удаляем двойные пробелы
                    type_of_operation = re.sub(" +", " ", key[3].lower())

                    # Онлайн редактор регулярных выражений, очень крутой - https://regex101.com/r/aGn8QC/2
                    # Полезная статья - https://habr.com/ru/post/349860/
                    if (re.fullmatch("поставлены на торги средства клиента.+перевод на фс ммвб.+", type_of_operation) or
                            re.fullmatch("поставлены на торги средства клиента.+перевод с фс ммвб.+",
                                         type_of_operation) or
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
                        name_of_share = re.search("(?<=дивиденды )(.+?)(?=-?\d* налог к удержанию)",
                                                  type_of_operation).group()
                        name_of_share = name_of_share.replace("-", " ")
                        shares_by_div = list(filter(lambda x: x.name.lower() == name_of_share, self.xml_shares_mapping))
                        if len(shares_by_div) != 1:
                            # Если не нашли по полному совпадению пытаемся искать регуляркой, возможные окончания: ао, aoo, апо
                            # Ищем именно АО, т. к. на бирже могут быть только такие ЮЛ
                            if name_of_share.endswith("-ао"):
                                shares_by_div = list(
                                    filter(
                                        lambda x: x.name.lower() == name_of_share.removesuffix("-ао").replace("-", " "),
                                        self.xml_shares_mapping))
                                if len(shares_by_div) != 1:
                                    raise Exception(
                                        "Error in search shares by div, count of items-{}".format(len(shares_by_div)))
                        new_money_deal.share_by_divident = Share.objects.get(isin=shares_by_div[0].isin)

                        # Ищем подходящую строку с налогом
                        # Почему здесь, а не в отдельном условии: (1)потому что важен порядок, на момент обработки строчки с налогом, записи с дивидендом может еще не быть; (2) налог схлопываем в одну строчку с дивидендом
                        tax_items = list(filter(lambda x: re.sub(" +", " ", x.attrib["comment"].lower()).startswith(
                            'удержан налог на доход по дивидендам {}'.format(name_of_share)) and x.attrib[
                                                              'operation_date'] == key[1],
                                                money_deal_items_xml))
                        if len(tax_items) > 1:
                            raise Exception("Lenght of tax_items for {} is {}".format(name_of_share, len(tax_items)))
                        elif len(tax_items) == 1:
                            # Валюта у дивиденда и налога должна быть одна
                            if tax_items[0].attrib['currency_code'] != key[0]:
                                raise Exception("Different currencies for dividend and tax of dividend")
                            new_money_deal.tax = tax_items[0].attrib['amount']

                    elif re.fullmatch("удержан налог на доход по дивидендам.+", type_of_operation):
                        # Пропускаем, т. к. налог учитываем сразу по строчке с дивидендом
                        continue

                    # Если тип не смогли определить - кидаем ошибку, чтобы сразу подсветить проблему, а не находить ее спустя какое-то время в данных
                    if new_money_deal.type_of_deal is None:
                        raise Exception("Unsupported type_of_deal for text='{}'".format(type_of_operation))

                    new_money_deal.currency = Currency.objects.get(code=key[0])
                    new_money_deal.datetime = key[1]
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
                raise Exception("Exception from parse money_deal_items_xml, text of key:begin {} end".format(
                    key)) from ex
