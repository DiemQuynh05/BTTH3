from django.contrib import admin

from .models import CandidateProfile, CandidateSkill, Resume

admin.site.register([CandidateProfile, CandidateSkill, Resume])
