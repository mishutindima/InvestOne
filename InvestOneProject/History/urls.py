from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('import-data', views.import_data, name='import_data'),
    path('import-data-result/<int:import_brocker_data_log_id>/', views.import_data_result, name='import_data_result'),
]
