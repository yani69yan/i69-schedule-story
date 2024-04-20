# Generated by Django 3.1.5 on 2022-11-27 10:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0022_deletedmessage"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeletedMessageDate",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("no_of_days", models.IntegerField(default=0)),
            ],
        ),
    ]
