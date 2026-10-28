from django import forms

from .models import EmployerProfile


class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ("company_name", "industry", "address", "website", "description", "logo")
