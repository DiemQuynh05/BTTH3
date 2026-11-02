from django.contrib import admin

from .models import Job, JobSkill, Skill

admin.site.register([Job, JobSkill, Skill])
