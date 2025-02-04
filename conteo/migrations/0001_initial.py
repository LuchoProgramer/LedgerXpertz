# Generated by Django 4.2.8 on 2025-01-25 20:50

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ConteoDiario",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("fecha_conteo", models.DateField(auto_now_add=True)),
                ("cantidad_contada", models.IntegerField()),
            ],
        ),
    ]
