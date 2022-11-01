from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ImportBrockerDataLog
from .services.parse_brocker_data_service import ParseBrockerDataService
import threading


def start_parse_report(import_brocker_data_log: ImportBrockerDataLog):
    service = ParseBrockerDataService()
    service.execute(import_brocker_data_log)


# Сразу после сохранения запускаем в асинхроне парсинг полученного отчета
@receiver(post_save, sender=ImportBrockerDataLog)
def on_import_brocker_data_log_save(sender, instance, **kwargs):
    if kwargs['created']:  # just on creation
        start_parse_report(instance)
        # TODO Разобраться как правильно запустить процесс в асинхроне и парсить отчеты
        # threading.Thread(target=start_parse_report, args=(instance)).start()
