from django.urls import path

from .views import (
    GewasperceelDetailView,
    admin_log_content,
    admin_logs,
    admin_status,
    health_check,
)

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("percelen/<int:pk>/", GewasperceelDetailView.as_view(), name="perceel-detail"),
    path("admin/status/", admin_status, name="admin-status"),
    path("admin/logs/", admin_logs, name="admin-logs"),
    path("admin/logs/<str:name>/", admin_log_content, name="admin-log-content"),
]
