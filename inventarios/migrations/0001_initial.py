# Generated by Django 4.2.8 on 2025-01-25 20:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Transferencia",
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
                ("cantidad", models.IntegerField()),
                ("fecha", models.DateTimeField(auto_now_add=True)),
                (
                    "producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="core.producto"
                    ),
                ),
                (
                    "sucursal_destino",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transferencias_entrada",
                        to="core.sucursal",
                    ),
                ),
                (
                    "sucursal_origen",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transferencias_salida",
                        to="core.sucursal",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MovimientoInventario",
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
                (
                    "tipo_movimiento",
                    models.CharField(
                        choices=[
                            ("COMPRA", "Compra"),
                            ("TRANSFERENCIA_ENTRADA", "Transferencia Entrada"),
                            ("TRANSFERENCIA_SALIDA", "Transferencia Salida"),
                            ("VENTA", "Venta"),
                        ],
                        max_length=25,
                    ),
                ),
                ("cantidad", models.IntegerField()),
                ("fecha", models.DateTimeField(auto_now_add=True)),
                (
                    "producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="core.producto"
                    ),
                ),
                (
                    "sucursal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="core.sucursal"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Inventario",
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
                ("cantidad", models.IntegerField()),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                (
                    "producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="core.producto"
                    ),
                ),
                (
                    "sucursal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="core.sucursal"
                    ),
                ),
            ],
            options={
                "unique_together": {("producto", "sucursal")},
            },
        ),
    ]
