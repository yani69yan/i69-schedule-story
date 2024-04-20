# Generated by Django 3.1.5 on 2022-10-24 15:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("defaultPicker", "0002_language"),
        ("user", "0024_auto_20221024_1246"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="worker_id_code",
            field=models.IntegerField(default=0, editable=False),
        ),
        migrations.AlterField(
            model_name="user",
            name="language",
            field=models.ManyToManyField(blank=True, to="defaultPicker.language"),
        ),
    ]
