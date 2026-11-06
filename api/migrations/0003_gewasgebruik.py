# Generated manually for veevoer/voedsel lookup

from django.db import migrations, models


def seed_gewas_gebruik(apps, schema_editor):
    Gewasperceel = apps.get_model("api", "Gewasperceel")
    GewasGebruik = apps.get_model("api", "GewasGebruik")

    from api.brp_constants import EXCLUDED_MBTILES_CATEGORIES
    from api.gewasgebruik_seed import seed_gewas_gebruik_from_queryset

    qs = Gewasperceel.objects.exclude(category__in=EXCLUDED_MBTILES_CATEGORIES)
    seed_gewas_gebruik_from_queryset(qs, GewasGebruikModel=GewasGebruik)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_gewasperceel_area_m2"),
    ]

    operations = [
        migrations.CreateModel(
            name="GewasGebruik",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("gewascode", models.IntegerField(db_index=True, unique=True)),
                (
                    "gebruik",
                    models.CharField(
                        choices=[
                            ("veevoer", "Veevoer"),
                            ("voedsel", "Voedsel (menselijke consumptie)"),
                            ("gemengd", "Gemengd / onbekend eindgebruik"),
                            (
                                "niet_voedsel",
                                "Niet voedsel of veevoer (sierteelt, braak, industrie, enz.)",
                            ),
                            ("onbekend", "Onbekend"),
                        ],
                        max_length=20,
                    ),
                ),
                ("toelichting", models.CharField(blank=True, max_length=200)),
            ],
            options={
                "ordering": ("gewascode",),
            },
        ),
        migrations.RunPython(seed_gewas_gebruik, noop_reverse),
    ]
