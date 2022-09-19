from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('history', views.index, name='index'),
    path('history/import-data', views.import_data, name='import_data')
]
