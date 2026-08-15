from django.urls import path

from .views import GewasperceelDetailView, health_check

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("percelen/<int:pk>/", GewasperceelDetailView.as_view(), name="perceel-detail"),
]
