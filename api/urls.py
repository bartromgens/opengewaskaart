from django.urls import path

from .views import (
    GewasperceelDetailView,
    admin_log_content,
    admin_logs,
    admin_status,
    categorieen_summary,
    gebruik_summary,
    gewassen_summary,
    gewas_gebruik_list,
    health_check,
)

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("gewassen/", gewassen_summary, name="gewassen-summary"),
    path("gewasgebruik/", gewas_gebruik_list, name="gewasgebruik-list"),
    path("gebruik/", gebruik_summary, name="gebruik-summary"),
    path("categorieen/", categorieen_summary, name="categorieen-summary"),
    path("percelen/<int:pk>/", GewasperceelDetailView.as_view(), name="perceel-detail"),
    path("admin/status/", admin_status, name="admin-status"),
    path("admin/logs/", admin_logs, name="admin-logs"),
    path("admin/logs/<str:name>/", admin_log_content, name="admin-log-content"),
]
