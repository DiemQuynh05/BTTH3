from django_app.views import health
from django.urls import path


urlpatterns = [
    path("health/", health, name="health"),
]
