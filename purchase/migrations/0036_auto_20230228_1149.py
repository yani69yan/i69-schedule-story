# Generated by Django 3.1.5 on 2023-02-28 11:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0035_auto_20230221_1011'),
    ]

    operations = [
        migrations.AlterField(
            model_name='permission',
            name='name',
            field=models.CharField(choices=[('SHARE_MOMENT', 'SHARE_MOMENT'), ('SHARE_USER_LOCATION', 'SHARE_USER_LOCATION'), ('REQUEST_USER_PRIVATE_ALBUM_ACCESS', 'REQUEST_USER_PRIVATE_ALBUM_ACCESS'), ('SHARE_STORY', 'SHARE_STORY'), ('FIRST_FREE_MESSAGE', 'FIRST_FREE_MESSAGE'), ('RANDOM_SEARCHED_USER_RESULTS_LIMIT', 'RANDOM_SEARCHED_USER_RESULTS_LIMIT'), ('POPULAR_SEARCHED_USER_RESULTS_LIMIT', 'POPULAR_SEARCHED_USER_RESULTS_LIMIT'), ('MOST_ACTIVE_SEARCHED_USER_RESULTS_LIMIT', 'MOST_ACTIVE_SEARCHED_USER_RESULTS_LIMIT'), ('COMMENT_UNLIMITED_MOMENT', 'COMMENT_UNLIMITED_MOMENT'), ('COMMENT_UNLIMITED_STORY', 'COMMENT_UNLIMITED_STORY'), ('SEE_WHO_VISITED_YOUR_PROFILE', 'SEE_WHO_VISITED_YOUR_PROFILE'), ('BE_NOTIFIED_FIRST_WHEN_THERE_IS_NEW_USER_IN_YOUR_AREA', 'BE_NOTIFIED_FIRST_WHEN_THERE_IS_NEW_USER_IN_YOUR_AREA'), ('VIEW_WHO_READ(SEEN)_YOUR_sent_MESSAGE', 'VIEW_WHO_READ(SEEN)_YOUR_sent_MESSAGE')], max_length=255, unique=True),
        ),
    ]
