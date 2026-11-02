from django.urls import path

from .views import delete_resume, profile

urlpatterns = [
    path("profile/", profile, name="candidate-profile"),
    path("resumes/<int:pk>/delete/", delete_resume, name="resume-delete"),
]
