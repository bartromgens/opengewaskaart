from django.db import models


class Gewasperceel(models.Model):
    jaar = models.IntegerField()
    gewascode = models.IntegerField()
    gewas = models.CharField(max_length=120)
    category = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
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
        ]

    def __str__(self) -> str:
        return f"{self.jaar} {self.gewas} ({self.gewascode})"
