from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import Bill, ImportBrockerDataLog
from .forms import ImportDataForm
from datetime import datetime
from .services.calc_sum_data_service import CalcSumDataService
from dataclasses import dataclass
from django.contrib.auth import authenticate, login

# Create your views here.
@dataclass
class BillInfo:
    bill: Bill
    share_balance: list[CalcSumDataService.ShareBalance]
    money_balance: list[CalcSumDataService.MoneyBalance]


def index(request):
    # if request.method == "GET":
    #     form=FilterByDateForm(request.GET)
    #     if form.is_valid():
    #
    #
    # TODO remove after add auth
    user = authenticate(request, username='admin', password='admin')
    if user is not None:
        login(request, user)

    bill_info = []
    for bill in Bill.objects.filter(owner=request.user):
        if bill.pk == 7:
            date_of_report = datetime(year=2020, month=12, day=31)
            bill_info.append(BillInfo(bill=bill,
                                      share_balance=CalcSumDataService.get_shares_balance_on_date(rep_bill=bill,
                                                                                                  date_of_report=date_of_report),
                                      money_balance=CalcSumDataService.get_money_balance_on_date(rep_bill=bill,
                                                                                                 date_of_report=date_of_report)))

    return render(request, 'history/index.html', {'user': request.user, 'bill_info': bill_info[0]})


def import_data(request):
    if request.method == "POST":

        # Создаём экземпляр формы и заполняем данными из запроса (связывание, binding):
        form = ImportDataForm(request.user, request.POST, request.FILES)

        if form.is_valid():
            import_brocker_data_log = ImportBrockerDataLog()
            import_brocker_data_log.bill = form.cleaned_data['bill']
            import_brocker_data_log.file_or_content = form.cleaned_data['input_brocker_file']
            import_brocker_data_log.save()

            return HttpResponseRedirect(reverse('import_data_result', args=[import_brocker_data_log.id]))

    # Если это GET (или какой-либо ещё), создать форму по умолчанию.
    else:
        form = ImportDataForm(request.user)

    return render(request, 'history/import-data-simple.html', {'form': form})


def import_data_result(request, import_brocker_data_log_id):
    import_brocker_data_log = get_object_or_404(ImportBrockerDataLog, pk=import_brocker_data_log_id)
    return render(request, 'history/import-data-result.html', {'import_brocker_data_log': import_brocker_data_log})
