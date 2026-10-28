from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("jobs.urls")),
    path("accounts/", include("accounts.urls")),
    path("candidates/", include("candidates.urls")),
    path("employers/", include("employers.urls")),
    path("applications/", include("applications.urls")),
]

handler403 = "django_app.views.error_403"
handler404 = "django_app.views.error_404"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
