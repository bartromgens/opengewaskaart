from django.db import models


class GewasGebruik(models.Model):
    """BRP gewascode → feed/food/industry classification for map colouring and aggregates."""

    GEBRUIK_VEEVOER = "veevoer"
    GEBRUIK_VOEDSEL = "voedsel"
    GEBRUIK_GEMENGD = "gemengd"
    GEBRUIK_NIET_VOEDSEL = "niet_voedsel"
    GEBRUIK_ONBEKEND = "onbekend"

    GEBRUIK_CHOICES = (
        (GEBRUIK_VEEVOER, "Veevoer"),
        (GEBRUIK_VOEDSEL, "Voedsel (menselijke consumptie)"),
        (GEBRUIK_GEMENGD, "Gemengd / onbekend eindgebruik"),
        (GEBRUIK_NIET_VOEDSEL, "Niet voedsel of veevoer (sierteelt, braak, industrie, enz.)"),
        (GEBRUIK_ONBEKEND, "Onbekend"),
    )

    gewascode = models.IntegerField(unique=True, db_index=True)
    gebruik = models.CharField(max_length=20, choices=GEBRUIK_CHOICES)
    toelichting = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ("gewascode",)

    def __str__(self) -> str:
        return f"{self.gewascode} → {self.gebruik}"


class Gewasperceel(models.Model):
    jaar = models.IntegerField()
    gewascode = models.IntegerField()
    gewas = models.CharField(max_length=120)
    category = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    # Parcel area in m² (RD), from ST_Area(geom) at ingest or backfill.
    area_m2 = models.FloatField(null=True, blank=True)
    geometry = models.TextField()
    min_lon = models.FloatField()
    min_lat = models.FloatField()
    max_lon = models.FloatField()
    max_lat = models.FloatField()
    geometry_hash = models.CharField(max_length=40)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["jaar", "geometry_hash"],
                name="unique_gewasperceel_jaar_geometry_hash",
            ),
        ]
        indexes = [
            models.Index(fields=["jaar"]),
            models.Index(fields=["gewascode"]),
            models.Index(fields=["min_lon", "max_lon", "min_lat", "max_lat"]),
            # National summaries aggregate these columns. Without this, SQLite
            # reads the geometry text for every parcel (the bulk of the file).
            models.Index(
                fields=["category", "gewascode", "gewas", "area_m2"],
                name="gewasperceel_summary_cover",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.jaar} {self.gewas} ({self.gewascode})"
