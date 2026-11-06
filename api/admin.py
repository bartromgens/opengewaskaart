from django.contrib import admin

from .models import GewasGebruik, Gewasperceel


@admin.register(GewasGebruik)
class GewasGebruikAdmin(admin.ModelAdmin):
    list_display = ("gewascode", "gebruik", "toelichting")
    list_filter = ("gebruik",)
    search_fields = ("gewascode", "toelichting")


@admin.register(Gewasperceel)
class GewasperceelAdmin(admin.ModelAdmin):
    list_display = ("jaar", "gewas", "gewascode", "category", "status")
    list_filter = ("jaar", "category")
    search_fields = ("gewas", "category", "status")
    readonly_fields = (
        "jaar",
        "gewascode",
        "gewas",
        "category",
        "status",
        "geometry",
        "min_lon",
        "min_lat",
        "max_lon",
        "max_lat",
        "geometry_hash",
    )
