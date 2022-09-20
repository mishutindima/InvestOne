from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from .models import User, Bill


# Create your views here.
def index(request):
    user = authenticate(request, username='admin', password='admin')
    if user is not None:
        login(request, user)
    return render(request, 'history/index.html', {'user': user})


def import_data(request):
    bills = Bill.objects.filter(owner=request.user)
    return render(request, 'history/import-data.html', {"bills": bills})
