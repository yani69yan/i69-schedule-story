# Generated by Django 3.1.5 on 2022-03-13 14:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reported_users",
            name="timestamp",
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
