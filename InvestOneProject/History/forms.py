from django import forms
from .models import Bill
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class ImportDataForm(forms.Form):
    bill = forms.ChoiceField(widget=forms.Select, help_text="Выберите счет, по которому хотите выполнить загрузку",
                             required=True)
    input_brocker_file = forms.FileField(allow_empty_file=False, help_text="Выберите файл для загрузки", required=True)

    def __init__(self, user, *args, **kwards):
        super(ImportDataForm, self).__init__(*args, **kwards)
        self.fields["bill"].choices = Bill.objects.filter(owner=user.id).values_list('id', 'brocker_name')

    def clean_bill(self):
        bill_id = self.cleaned_data["bill"]
        bill_object = Bill.objects.get(pk=bill_id)

        return bill_object

    def clean_input_brocker_file(self):
        file = self.cleaned_data["input_brocker_file"]

        if file.content_type == "text/xml":
            return file
        else:
            raise ValidationError(_('This type of file ({0}) is not supported!'.format(file.content_type)))
