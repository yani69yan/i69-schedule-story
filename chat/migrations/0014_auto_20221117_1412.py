# Generated by Django 3.1.5 on 2022-11-17 14:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0013_auto_20221019_1118"),
    ]

    operations = [
        migrations.AddField(
            model_name="broadcast",
            name="content_ar",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_br",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_cs",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_da",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_de",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_el",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_es",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_es_419",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_fa",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_fi",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_hr",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_it",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_iw",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_ja",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_ko",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_nl",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_nn",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_no",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_pl",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_pt_br",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_pt_pt",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_ru",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_sl",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_sv",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_sw",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_tl",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_uk",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_vi",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_zh_cn",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="broadcast",
            name="content_zh_tw",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_ar",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_br",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_cs",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_da",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_de",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_el",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_es",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_es_419",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_fa",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_fi",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_hr",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_it",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_iw",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_ja",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_ko",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_nl",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_nn",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_no",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_pl",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_pt_br",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_pt_pt",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_ru",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_sl",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_sv",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_sw",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_tl",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_uk",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_vi",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_zh_cn",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
        migrations.AddField(
            model_name="firstmessage",
            name="content_zh_tw",
            field=models.CharField(blank=True, max_length=265, null=True),
        ),
    ]
