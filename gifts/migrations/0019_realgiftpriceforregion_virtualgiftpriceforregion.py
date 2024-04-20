# Generated by Django 3.1.5 on 2023-02-07 18:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0046_auto_20230206_1809'),
        ('gifts', '0018_auto_20221125_1717'),
    ]

    operations = [
        migrations.CreateModel(
            name='VirtualGiftPriceForRegion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cost', models.FloatField()),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.coinsettingsregion')),
                ('virtual_gift', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gifts.virtualgift')),
            ],
        ),
        migrations.CreateModel(
            name='RealGiftPriceForRegion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cost', models.FloatField()),
                ('real_gift', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gifts.realgift')),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.coinsettingsregion')),
            ],
        ),
    ]
