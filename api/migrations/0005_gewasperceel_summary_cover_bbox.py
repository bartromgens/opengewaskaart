from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0004_gewasperceel_summary_cover"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="gewasperceel",
            name="gewasperceel_summary_cover",
        ),
        migrations.AddIndex(
            model_name="gewasperceel",
            index=models.Index(
                fields=[
                    "category",
                    "gewascode",
                    "gewas",
                    "area_m2",
                    "min_lon",
                    "max_lon",
                    "min_lat",
                    "max_lat",
                ],
                name="gewasperceel_summary_cover",
            ),
        ),
    ]
