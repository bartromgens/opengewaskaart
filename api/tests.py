import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from api.models import GewasGebruik, Gewasperceel
from api.management.bbox import parse_bbox
from api.management.commands.geojson_to_mbtiles import validate_geojson_has_features
from api.brp_constants import EXCLUDED_MBTILES_CATEGORIES
from api.gewasgebruik_seed import classify_gewas
from api.management.tippecanoe import (
    build_tippecanoe_command,
    ensure_min_tippecanoe_version,
    format_version,
    parse_tippecanoe_version,
)


class GewasGebruikClassifyTests(TestCase):
    def test_grain_codes_are_gemengd(self) -> None:
        self.assertEqual(classify_gewas(233, "Tarwe, winter-", "Bouwland"), GewasGebruik.GEBRUIK_GEMENGD)

    def test_snijmais_is_veevoer(self) -> None:
        self.assertEqual(classify_gewas(259, "Mais, snij-", "Bouwland"), GewasGebruik.GEBRUIK_VEEVOER)

    def test_grasland_category_defaults_veevoer(self) -> None:
        self.assertEqual(classify_gewas(99999, "Onbekend gras", "Grasland"), GewasGebruik.GEBRUIK_VEEVOER)


class BboxTests(TestCase):
    def test_utrecht_bbox(self) -> None:
        bbox = parse_bbox("utrecht")
        self.assertEqual(bbox, (4.792, 51.858, 5.627, 52.302))


class GeojsonValidationTests(TestCase):
    def test_validate_geojson_has_features_accepts_non_empty_file(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "input.geojson"
            path.write_text(
                '{"type":"FeatureCollection","features":[{"type":"Feature","geometry":null,"properties":{}}]}',
                encoding="utf-8",
            )
            validate_geojson_has_features(path)

    def test_validate_geojson_has_features_rejects_empty_file(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.geojson"
            path.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
            with self.assertRaises(CommandError):
                validate_geojson_has_features(path)

    def test_validate_geojson_has_features_rejects_invalid_json(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "invalid.geojson"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(CommandError):
                validate_geojson_has_features(path)


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

        with patch(
            "api.management.tippecanoe.get_tippecanoe_version",
            return_value=(2, 79, 0),
        ):
            with self.assertRaises(CommandError):
                ensure_min_tippecanoe_version("/tmp/tippecanoe", (2, 80, 0))


class TippecanoeCommandTests(TestCase):
    def test_build_tippecanoe_command_omits_drop_flags_by_default(self) -> None:
        with TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.geojson"
            output_path = Path(tmpdir) / "output.mbtiles"
            input_path.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")

            command = build_tippecanoe_command(
                tippecanoe_path="/usr/bin/tippecanoe",
                input_path=input_path,
                output_path=output_path,
                layer_name="percelen",
                min_zoom=5,
                max_zoom=16,
                maximum_tile_bytes=2_000_000,
                maximum_tile_features=1_000_000,
                full_detail=12,
                low_detail=12,
                minimum_detail=9,
                simplification=15,
                coalesce_densest=False,
                drop_densest=False,
                drop_smallest=False,
                drop_fraction=True,
                bbox=None,
                force=False,
            )

        self.assertIn("--minimum-detail", command)
        self.assertIn("9", command)
        self.assertIn("--maximum-tile-features", command)
        self.assertIn("1000000", command)
        self.assertIn("--drop-fraction-as-needed", command)
        self.assertNotIn("--coalesce-densest-as-needed", command)
        self.assertNotIn("--drop-densest-as-needed", command)
        self.assertNotIn("--drop-smallest-as-needed", command)

    def test_build_tippecanoe_command_can_enable_coalesce(self) -> None:
        with TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.geojson"
            output_path = Path(tmpdir) / "output.mbtiles"
            input_path.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")

            command = build_tippecanoe_command(
                tippecanoe_path="/usr/bin/tippecanoe",
                input_path=input_path,
                output_path=output_path,
                layer_name="percelen",
                min_zoom=5,
                max_zoom=16,
                maximum_tile_bytes=2_000_000,
                maximum_tile_features=1_000_000,
                full_detail=12,
                low_detail=12,
                minimum_detail=9,
                simplification=15,
                coalesce_densest=True,
                drop_densest=False,
                drop_smallest=False,
                drop_fraction=False,
                bbox=None,
                force=False,
            )

        self.assertIn("--coalesce-densest-as-needed", command)
        self.assertNotIn("--drop-densest-as-needed", command)


class GewassenSummaryViewTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.geometry = json.dumps(
            {
                "type": "Polygon",
                "coordinates": [[[5.3, 52.2], [5.31, 52.2], [5.31, 52.21], [5.3, 52.21], [5.3, 52.2]]],
            }
        )
        self.common = {
            "jaar": 2025,
            "status": "Definitief",
            "geometry": self.geometry,
            "min_lon": 5.3,
            "min_lat": 52.2,
            "max_lon": 5.31,
            "max_lat": 52.21,
        }
        Gewasperceel.objects.create(
            gewascode=201,
            gewas="Wintertarwe",
            category="Granen",
            area_m2=1000.0,
            geometry_hash="g1",
            **self.common,
        )
        Gewasperceel.objects.create(
            gewascode=201,
            gewas="Wintertarwe",
            category="Granen",
            area_m2=500.0,
            geometry_hash="g2",
            **self.common,
        )
        Gewasperceel.objects.create(
            gewascode=305,
            gewas="Aardappel, consumptie-",
            category="Aardappelen",
            area_m2=100.0,
            geometry_hash="a1",
            **self.common,
        )
        Gewasperceel.objects.create(
            gewascode=901,
            gewas="Houtwal",
            category="Landschapselement",
            area_m2=200.0,
            geometry_hash="l1",
            **self.common,
        )

    def test_gewassen_summary_aggregates_and_excludes_landschap(self) -> None:
        url = reverse("gewassen-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        row0 = data[0]
        self.assertEqual(row0["gewascode"], 201)
        self.assertEqual(row0["gewas"], "Wintertarwe")
        self.assertEqual(row0["category"], "Granen")
        self.assertEqual(row0["parcel_count"], 2)
        self.assertAlmostEqual(row0["area_m2"], 1500.0)
        row1 = data[1]
        self.assertEqual(row1["gewascode"], 305)
        self.assertEqual(row0["gebruik"], GewasGebruik.GEBRUIK_ONBEKEND)
        self.assertEqual(row1["gebruik"], GewasGebruik.GEBRUIK_ONBEKEND)

    def test_gewassen_summary_limit_returns_top_row(self) -> None:
        url = reverse("gewassen-summary")
        response = self.client.get(url, {"limit": "1"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["gewascode"], 201)

    def test_gewassen_summary_invalid_limit(self) -> None:
        url = reverse("gewassen-summary")
        self.assertEqual(self.client.get(url, {"limit": "x"}).status_code, 400)
        self.assertEqual(self.client.get(url, {"limit": "0"}).status_code, 400)

    def test_gewassen_summary_invalid_jaar(self) -> None:
        url = reverse("gewassen-summary")
        response = self.client.get(url, {"jaar": "x"})
        self.assertEqual(response.status_code, 400)

    def test_gewassen_summary_includes_gebruik_from_lookup(self) -> None:
        GewasGebruik.objects.create(gewascode=201, gebruik=GewasGebruik.GEBRUIK_GEMENGD)
        url = reverse("gewassen-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        by_code = {row["gewascode"]: row for row in response.json()}
        self.assertEqual(by_code[201]["gebruik"], GewasGebruik.GEBRUIK_GEMENGD)
        self.assertEqual(by_code[305]["gebruik"], GewasGebruik.GEBRUIK_ONBEKEND)


class GewasGebruikListViewTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        GewasGebruik.objects.create(gewascode=233, gebruik=GewasGebruik.GEBRUIK_GEMENGD)
        GewasGebruik.objects.create(gewascode=259, gebruik=GewasGebruik.GEBRUIK_VEEVOER)

    def test_gewasgebruik_list_ordered(self) -> None:
        url = reverse("gewasgebruik-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["gewascode"], 233)
        self.assertEqual(data[0]["gebruik"], GewasGebruik.GEBRUIK_GEMENGD)
        self.assertEqual(data[1]["gewascode"], 259)


class GebruikSummaryViewTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.geometry = json.dumps(
            {
                "type": "Polygon",
                "coordinates": [[[5.3, 52.2], [5.31, 52.2], [5.31, 52.21], [5.3, 52.21], [5.3, 52.2]]],
            }
        )
        self.common = {
            "jaar": 2025,
            "status": "Definitief",
            "geometry": self.geometry,
            "min_lon": 5.3,
            "min_lat": 52.2,
            "max_lon": 5.31,
            "max_lat": 52.21,
        }
        GewasGebruik.objects.create(gewascode=201, gebruik=GewasGebruik.GEBRUIK_GEMENGD)
        GewasGebruik.objects.create(gewascode=202, gebruik=GewasGebruik.GEBRUIK_VEEVOER)
        Gewasperceel.objects.create(
            gewascode=201,
            gewas="Wintertarwe",
            category="Granen",
            area_m2=1000.0,
            geometry_hash="g1",
            **self.common,
        )
        Gewasperceel.objects.create(
            gewascode=202,
            gewas="Gras",
            category="Grasland",
            area_m2=2000.0,
            geometry_hash="g2",
            **self.common,
        )
        Gewasperceel.objects.create(
            gewascode=901,
            gewas="Houtwal",
            category="Landschapselement",
            area_m2=500.0,
            geometry_hash="l1",
            **self.common,
        )

    def test_gebruik_summary_excludes_landschap_and_orders(self) -> None:
        url = reverse("gebruik-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        by_gebruik = {row["gebruik"]: row for row in data}
        self.assertEqual(by_gebruik[GewasGebruik.GEBRUIK_VEEVOER]["parcel_count"], 1)
        self.assertAlmostEqual(by_gebruik[GewasGebruik.GEBRUIK_VEEVOER]["area_m2"], 2000.0)
        self.assertEqual(by_gebruik[GewasGebruik.GEBRUIK_GEMENGD]["parcel_count"], 1)
        # Five buckets always present
        self.assertEqual(len(data), 5)

    def test_gebruik_summary_invalid_jaar(self) -> None:
        url = reverse("gebruik-summary")
        response = self.client.get(url, {"jaar": "x"})
        self.assertEqual(response.status_code, 400)


class CategorieenSummaryViewTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.geometry = json.dumps(
            {
                "type": "Polygon",
                "coordinates": [[[5.3, 52.2], [5.31, 52.2], [5.31, 52.21], [5.3, 52.21], [5.3, 52.2]]],
            }
        )
        self.common = {
            "jaar": 2025,
            "status": "Definitief",
            "geometry": self.geometry,
            "min_lon": 5.3,
            "min_lat": 52.2,
            "max_lon": 5.31,
            "max_lat": 52.21,
        }
        Gewasperceel.objects.create(
            gewascode=201,
            gewas="Wintertarwe",
            category="Bouwland",
            area_m2=1000.0,
            geometry_hash="b1",
            **self.common,
        )
        Gewasperceel.objects.create(
            gewascode=202,
            gewas="Gras",
            category="Grasland",
            area_m2=3000.0,
            geometry_hash="g1",
            **self.common,
        )
        Gewasperceel.objects.create(
            gewascode=902,
            gewas="Heg",
            category="Landschapselement",
            area_m2=50.0,
            geometry_hash="l1",
            **self.common,
        )
        Gewasperceel.objects.create(
            gewascode=903,
            gewas="Houtwal",
            category="Landschapselement",
            area_m2=150.0,
            geometry_hash="l2",
            **self.common,
        )

    def test_categorieen_summary_excludes_landschap(self) -> None:
        url = reverse("categorieen-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        by_cat = {row["category"]: row for row in data}
        self.assertEqual(by_cat["Grasland"]["parcel_count"], 1)
        self.assertAlmostEqual(by_cat["Grasland"]["area_m2"], 3000.0)
        self.assertEqual(by_cat["Bouwland"]["parcel_count"], 1)
        self.assertAlmostEqual(by_cat["Bouwland"]["area_m2"], 1000.0)
        self.assertNotIn("Landschapselement", by_cat)

    def test_categorieen_summary_invalid_jaar(self) -> None:
        url = reverse("categorieen-summary")
        response = self.client.get(url, {"jaar": "x"})
        self.assertEqual(response.status_code, 400)


class GewasperceelDetailViewTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.parcel = Gewasperceel.objects.create(
            jaar=2025,
            gewascode=201,
            gewas="Wintertarwe",
            category="Granen",
            status="Definitief",
            area_m2=None,
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
        data = response.json()
        self.assertEqual(data["gewas"], "Wintertarwe")
        self.assertEqual(data["geometry"]["type"], "Polygon")
        self.assertEqual(data["gebruik"], GewasGebruik.GEBRUIK_ONBEKEND)

    def test_retrieve_missing_parcel(self) -> None:
        url = reverse("perceel-detail", kwargs={"pk": 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class ExportGewaspercelenGeojsonTests(TestCase):
    def setUp(self) -> None:
        self.geometry = json.dumps(
            {
                "type": "Polygon",
                "coordinates": [[[5.3, 52.2], [5.31, 52.2], [5.31, 52.21], [5.3, 52.21], [5.3, 52.2]]],
            }
        )
        self.common = {
            "jaar": 2025,
            "status": "Definitief",
            "geometry": self.geometry,
            "min_lon": 5.3,
            "min_lat": 52.2,
            "max_lon": 5.31,
            "max_lat": 52.21,
        }
        Gewasperceel.objects.create(
            gewascode=201,
            gewas="Wintertarwe",
            category="Granen",
            geometry_hash="granen1",
            **self.common,
        )
        Gewasperceel.objects.create(
            gewascode=901,
            gewas="Houtwal",
            category="Landschapselement",
            geometry_hash="landschap1",
            **self.common,
        )

    def test_excludes_landschapselement_from_export(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            output_path = f"{tmpdir}/export.geojson"
            call_command(
                "export_gewaspercelen_geojson",
                output=output_path,
                stdout=StringIO(),
            )
            payload = json.loads(open(output_path, encoding="utf-8").read())

        categories = {feature["properties"]["category"] for feature in payload["features"]}
        self.assertEqual(len(payload["features"]), 1)
        self.assertIn("Granen", categories)
        self.assertNotIn("Landschapselement", categories)
        self.assertIn("Landschapselement", EXCLUDED_MBTILES_CATEGORIES)
