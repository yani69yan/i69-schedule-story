# Generated by Django 3.1.5 on 2023-05-10 10:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0031_restrictedmessages'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactUs',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('email', models.CharField(max_length=100)),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'Contact Us',
            },
        ),
    ]
