# Generated by Django 3.1.5 on 2022-01-22 07:00

from django.db import migrations, models
import moments.models


class Migration(migrations.Migration):

    dependencies = [
        ("moments", "0002_moment_title"),
    ]

    operations = [
        migrations.AlterField(
            model_name="moment",
            name="file",
            field=models.FileField(
                blank=True,
                max_length=500,
                null=True,
                upload_to=moments.models.Moment.get_avatar_path,
            ),
        ),
    ]
