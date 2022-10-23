from django.shortcuts import render, get_object_or_404
from django.contrib.auth import authenticate, login
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from .models import User, Bill, ImportBrockerDataLog
from .forms import ImportDataForm


# Create your views here.
def index(request):
    user = authenticate(request, username='admin', password='admin')
    if user is not None:
        login(request, user)
    return render(request, 'history/index.html', {'user': user})


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
