from django.urls import path

from .views import home, job_detail, job_list
from .dashboard_views import dashboard

urlpatterns = [
    path("", home, name="home"),
    path("jobs/", job_list, name="job-list"),
    path("jobs/<int:pk>/", job_detail, name="job-detail"),
    path("dashboard/", dashboard, name="dashboard"),
]
