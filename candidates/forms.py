from django import forms

from .models import CandidateProfile, Resume


class CandidateProfileForm(forms.ModelForm):
    class Meta:
        model = CandidateProfile
        fields = ("phone", "date_of_birth", "location", "education", "bio", "avatar")
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}


class ResumeForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ("file",)
