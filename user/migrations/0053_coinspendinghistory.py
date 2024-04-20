# Generated by Django 3.1.5 on 2023-02-24 20:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0052_featuresettings'),
    ]

    operations = [
        migrations.CreateModel(
            name='CoinSpendingHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('coins_spent', models.IntegerField()),
                ('description', models.CharField(blank=True, default=None, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_coin_spending_history', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]