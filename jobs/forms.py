from django import forms

from .models import Job, JobSkill


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ("title", "description", "requirements", "responsibilities", "location", "job_type", "salary_min", "salary_max", "experience_level", "status", "deadline")
        widgets = {"deadline": forms.DateInput(attrs={"type": "date"})}


class JobSkillForm(forms.ModelForm):
    class Meta:
        model = JobSkill
        fields = ("skill", "importance")
