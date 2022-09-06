from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Share)
admin.site.register(Bill)
admin.site.register(Currency)
admin.site.register(BrockerPeriodicCommissions)
admin.site.register(MoneyDeal)
admin.site.register(ShareDeal)
admin.site.register(CurrencyExchangeDeal)
admin.site.register(InvestRecommendation)