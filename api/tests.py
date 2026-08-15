import json

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from api.models import Gewasperceel
from api.management.tippecanoe import (
    ensure_min_tippecanoe_version,
    format_version,
    parse_tippecanoe_version,
)


class TippecanoeVersionTests(TestCase):
    def test_parse_tippecanoe_version(self) -> None:
        self.assertEqual(parse_tippecanoe_version("tippecanoe v2.80.0"), (2, 80, 0))
        self.assertEqual(parse_tippecanoe_version("2.81"), (2, 81, 0))
        self.assertIsNone(parse_tippecanoe_version("unknown"))

    def test_ensure_min_tippecanoe_version_accepts_new_enough(self) -> None:
        from unittest.mock import patch

        with patch(
            "api.management.tippecanoe.get_tippecanoe_version",
            return_value=(2, 80, 0),
        ):
            version = ensure_min_tippecanoe_version("/tmp/tippecanoe", (2, 80, 0))
        self.assertEqual(version, format_version((2, 80, 0)))

    def test_ensure_min_tippecanoe_version_rejects_old(self) -> None:
        from unittest.mock import patch

        from django.core.management.base import CommandError

        with patch(
            "api.management.tippecanoe.get_tippecanoe_version",
            return_value=(2, 79, 0),
        ):
            with self.assertRaises(CommandError):
                ensure_min_tippecanoe_version("/tmp/tippecanoe", (2, 80, 0))


class GewasperceelDetailViewTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.parcel = Gewasperceel.objects.create(
            jaar=2025,
            gewascode=201,
            gewas="Wintertarwe",
            category="Granen",
            status="Definitief",
            geometry=json.dumps(
                {
                    "type": "Polygon",
                    "coordinates": [[[5.3, 52.2], [5.31, 52.2], [5.31, 52.21], [5.3, 52.21], [5.3, 52.2]]],
                }
            ),
            min_lon=5.3,
            min_lat=52.2,
            max_lon=5.31,
            max_lat=52.21,
            geometry_hash="abc123",
        )

    def test_retrieve_parcel(self) -> None:
        url = reverse("perceel-detail", kwargs={"pk": self.parcel.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["gewas"], "Wintertarwe")
        self.assertEqual(response.json()["geometry"]["type"], "Polygon")

    def test_retrieve_missing_parcel(self) -> None:
        url = reverse("perceel-detail", kwargs={"pk": 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
