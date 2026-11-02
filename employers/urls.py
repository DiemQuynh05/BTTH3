from django.urls import include, path

from .views import profile

urlpatterns = [
    path("profile/", profile, name="employer-profile"),
    path("jobs/", include("jobs.employer_urls")),
]
