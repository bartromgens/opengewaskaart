import json

from rest_framework import serializers

from api.models import Gewasperceel


class GewassenSummarySerializer(serializers.Serializer):
    gewascode = serializers.IntegerField()
    gewas = serializers.CharField()
    category = serializers.CharField()
    parcel_count = serializers.IntegerField()
    area_m2 = serializers.FloatField(allow_null=True)


class CategorieSummarySerializer(serializers.Serializer):
    category = serializers.CharField()
    parcel_count = serializers.IntegerField()
    area_m2 = serializers.FloatField(allow_null=True)


class GewasperceelSerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()

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
        ]

    def get_geometry(self, obj: Gewasperceel) -> dict:
        return json.loads(obj.geometry)
