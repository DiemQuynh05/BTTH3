from django.urls import path
from .views_ai import cv_parse, match_preview, rescore_job, update_application_status
from .views_bi import bi_funnel, bi_salary, bi_skills, bi_summary, bi_trend

urlpatterns = [
    # AI Matching & Parsing endpoints
    path("match/preview/", match_preview, name="api-match-preview"),
    path("match/rescore/<int:job_id>/", rescore_job, name="api-match-rescore"),
    path("cv/parse/", cv_parse, name="api-cv-parse"),
    path("applications/<int:app_id>/status/", update_application_status, name="api-application-status"),

    # BI Dashboard endpoints
    path("bi/summary/", bi_summary, name="api-bi-summary"),
    path("bi/skills/", bi_skills, name="api-bi-skills"),
    path("bi/salary/", bi_salary, name="api-bi-salary"),
    path("bi/funnel/", bi_funnel, name="api-bi-funnel"),
    path("bi/trend/", bi_trend, name="api-bi-trend"),
]
