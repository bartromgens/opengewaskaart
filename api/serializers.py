import json

from rest_framework import serializers

from api.models import Gewasperceel


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
            "geometry",
        ]

    def get_geometry(self, obj: Gewasperceel) -> dict:
        return json.loads(obj.geometry)
