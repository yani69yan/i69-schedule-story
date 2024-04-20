# Generated by Django 3.1.5 on 2022-11-27 09:38

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0021_message_is_deleted"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeletedMessage",
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
                ("timestamp", models.DateTimeField(auto_now=True)),
                ("content", models.CharField(blank=True, max_length=5120)),
                ("deleted_timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "room_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="chat.room"
                    ),
                ),
                (
                    "user_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="DeletedSender",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-deleted_timestamp",),
            },
        ),
    ]
