from ..models import ImportBrockerDataLog
import traceback
from parse_brocker_data_by_open import ParseBrockerDataByOpen

# Цель класса - парсить брокерский отчет или данные
class ParseBrockerDataService:

    def execute(self, import_brocker_data_log: ImportBrockerDataLog) -> None:
        try:
            import_brocker_data_log.status_code = ImportBrockerDataLog.StatusCodeChoices.STARTED
            import_brocker_data_log.save()

            if import_brocker_data_log.bill.brocker_name == "Открытие":
                ParseBrockerDataByOpen().execute(import_brocker_data_log)

            import_brocker_data_log.status_code = ImportBrockerDataLog.StatusCodeChoices.FINISHED_SUCCESS
            import_brocker_data_log.save()

        except Exception as ex:
            import_brocker_data_log.status_code = ImportBrockerDataLog.StatusCodeChoices.ERROR
            import_brocker_data_log.error_text = "{}\r\n{}".format(repr(ex), traceback.format_exc())
            import_brocker_data_log.save()