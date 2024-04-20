# Generated by Django 3.1.5 on 2022-03-23 19:08

from django.db import migrations, models
import moments.models


class Migration(migrations.Migration):

    dependencies = [
        ("moments", "0015_comment_reply_to"),
    ]

    operations = [
        migrations.AddField(
            model_name="story",
            name="thumbnail",
            field=models.ImageField(
                null=True, upload_to=moments.models.Story.get_avatar_path
            ),
        ),
    ]
