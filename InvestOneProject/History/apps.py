from django.apps import AppConfig

class HistoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'History'

    def ready(self):
        # Implicitly connect signal handlers decorated with @receiver.
        from . import signals
