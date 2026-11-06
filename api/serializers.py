import json

from rest_framework import serializers

from api.models import Gewasperceel, GewasGebruik


class GewassenSummarySerializer(serializers.Serializer):
    gewascode = serializers.IntegerField()
    gewas = serializers.CharField()
    category = serializers.CharField()
    parcel_count = serializers.IntegerField()
    area_m2 = serializers.FloatField(allow_null=True)
    gebruik = serializers.SerializerMethodField()
    # True if this gewascode has a row in GewasGebruik (else API gebruik defaults to onbekend).
    gebruik_geclassificeerd = serializers.SerializerMethodField()

    def get_gebruik(self, obj: dict) -> str:
        mapping = self.context.get("gebruik_map") or {}
        return mapping.get(obj["gewascode"], GewasGebruik.GEBRUIK_ONBEKEND)

    def get_gebruik_geclassificeerd(self, obj: dict) -> bool:
        codes = self.context.get("gewas_gebruik_codes")
        if not codes:
            return False
        return obj["gewascode"] in codes


class CategorieSummarySerializer(serializers.Serializer):
    category = serializers.CharField()
    parcel_count = serializers.IntegerField()
    area_m2 = serializers.FloatField(allow_null=True)


class GewasperceelSerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()
    gebruik = serializers.SerializerMethodField()

    class Meta:
        model = Gewasperceel
        fields = [
            "id",
            "jaar",
            "gewascode",
            "gewas",
            "category",
            "status",
            "area_m2",
            "geometry",
            "gebruik",
        ]

    def get_geometry(self, obj: Gewasperceel) -> dict:
        return json.loads(obj.geometry)

    def get_gebruik(self, obj: Gewasperceel) -> str:
        mapping = self.context.get("gebruik_map") or {}
        return mapping.get(obj.gewascode, GewasGebruik.GEBRUIK_ONBEKEND)


class GewasGebruikSerializer(serializers.Serializer):
    gewascode = serializers.IntegerField()
    gebruik = serializers.CharField()


class GebruikSummarySerializer(serializers.Serializer):
    gebruik = serializers.CharField()
    parcel_count = serializers.IntegerField()
    area_m2 = serializers.FloatField(allow_null=True)
