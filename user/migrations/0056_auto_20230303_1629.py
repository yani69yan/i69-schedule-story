# Generated by Django 3.1.5 on 2023-03-03 16:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0055_userprofiletranlations'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserInterestedIn',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category_name', models.CharField(choices=[('SERIOUS_RELATIONSHIP', 'SERIOUS RELATIONSHIP'), ('CAUSAL_DATING', 'CAUSAL DATING'), ('NEW_FRIENDS', 'NEW FRIENDS'), ('ROOM_MATES', 'ROOM MATES'), ('BUSINESS_CONTACTS', 'BUSINESS CONTACTS')], max_length=95, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='userprofiletranlations',
            name='name',
            field=models.CharField(max_length=95, unique=True),
        ),
        migrations.CreateModel(
            name='HideUserInterestedIn',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.userinterestedin')),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.country')),
            ],
        ),
    ]