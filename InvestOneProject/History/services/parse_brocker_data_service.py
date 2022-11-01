from ..models import Currency, Share, ImportBrockerDataLog, ShareDeal, TypeOfDealsChoices
from dataclasses import dataclass
import xml.etree.ElementTree as ET


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
            import_brocker_data_log.error_text = repr(ex)
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
                                                                        exchange_name=item.attrib[
                                                                            "board_name"].strip(),
                                                                        currency_code=item.attrib[
                                                                            "nominal_curr"].strip())
                , xml_shares))

        # 1. Заключенные в отчетном периоде сделки купли/продажи с ценными бумагами
        xml_share_deals = root.findall('./spot_main_deals_conclusion/item')
        for xml_share_deal in xml_share_deals:
            xml_share_deal_id = xml_share_deal.attrib["request_no"]  # Номер заявки
            if ShareDeal.objects.filter(operation_number=xml_share_deal_id,
                                        bill=import_brocker_data_log.bill).exists() is False:

                # Такой операции нет, значит нужно добавлять -> идем дальше по коду цикла
                new_share_deal = ShareDeal(operation_number=xml_share_deal_id,
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
                shares_from_model = Share.objects.get(isin=shares_from_report[0].isin)
                if len(shares_from_model) > 1:
                    raise "Найдено несколько подходящих ЦБ по коду. Просьба проверить содержимое отчета"
                elif len(shares_from_model) == 0:
                    # Регистрируем новую ЦБ в справочнике
                    share_model = Share(isin=shares_from_report[0].isin,
                                        code=shares_from_report[0].code,
                                        name=shares_from_report[0].name,
                                        exchange_name=shares_from_report[0].exchange_name,
                                        currency=Currency.objects.get(code=shares_from_report[0].currency_code)[0])
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
                new_share_deal.bill = import_brocker_data_log.bill
                new_share_deal.datetime = xml_share_deal.attrib["conclusion_time"]
                new_share_deal.price = float(xml_share_deal.attrib["price"].strip())
                new_share_deal.commission = float(xml_share_deal.attrib["broker_commission"].strip())

                new_share_deal.save()

        # Заключенные в отчётном периоде биржевые конверсионные сделки, сделки с драгоценными металлами
        currency_exchange_deal = root.findall('./made_deal')

        # Прочие зачисления/списания денежных средств
        money_deals = root.findall('./unified_non_trade_money_operations')

        return None

    def _parse_brocker_report_vtb(self, import_brocker_data_log: ImportBrockerDataLog) -> None:
        pass
