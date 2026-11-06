from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="gewasperceel",
            name="area_m2",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
