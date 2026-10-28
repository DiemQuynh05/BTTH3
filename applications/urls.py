from django.urls import path

from .views import apply, application_list

urlpatterns = [
    path("", application_list, name="application-list"),
    path("apply/<int:job_id>/", apply, name="application-apply"),
]
