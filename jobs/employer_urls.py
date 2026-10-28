from django.urls import path

from .views import employer_job_create, employer_job_delete, employer_job_edit, employer_job_list

urlpatterns = [
    path("", employer_job_list, name="employer-job-list"),
    path("create/", employer_job_create, name="employer-job-create"),
    path("<int:pk>/edit/", employer_job_edit, name="employer-job-edit"),
    path("<int:pk>/delete/", employer_job_delete, name="employer-job-delete"),
]
