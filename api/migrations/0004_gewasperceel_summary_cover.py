from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0003_gewasgebruik"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="gewasperceel",
            index=models.Index(
                fields=["category", "gewascode", "gewas", "area_m2"],
                name="gewasperceel_summary_cover",
            ),
        ),
    ]
