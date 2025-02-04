from django.db import models
from django.core.exceptions import ValidationError
from core.models import Producto, Sucursal, Categoria, Presentacion  # Agregar esta línea para importar Producto y Sucursal

class Inventario(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)  # Ahora usamos Producto directamente
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('producto', 'sucursal')

    def __str__(self):
        return f'{self.producto.nombre} - {self.cantidad} unidades en {self.sucursal.nombre}'

    def clean(self):
        if self.cantidad < 0:
            raise ValidationError("La cantidad en inventario no puede ser negativa.")


class Transferencia(models.Model):
    sucursal_origen = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='transferencias_salida')
    sucursal_destino = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='transferencias_entrada')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)  # Usamos Producto directamente
    cantidad = models.IntegerField()
    fecha = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Lógica de transferencia
        inventario_origen = Inventario.objects.get(sucursal=self.sucursal_origen, producto=self.producto)
        if inventario_origen.cantidad < self.cantidad:
            raise ValueError("No hay suficiente inventario en la sucursal matriz para transferir.")
        
        inventario_origen.cantidad -= self.cantidad
        inventario_origen.save()

        # Actualizar inventario en la sucursal de destino
        inventario_destino, created = Inventario.objects.get_or_create(
            sucursal=self.sucursal_destino, 
            producto=self.producto
        )
        inventario_destino.cantidad += self.cantidad
        inventario_destino.save()

        # Registrar los movimientos de transferencia
        MovimientoInventario.objects.create(
            producto=self.producto,
            sucursal=self.sucursal_origen,
            tipo_movimiento='TRANSFERENCIA_SALIDA',
            cantidad=-self.cantidad
        )

        MovimientoInventario.objects.create(
            producto=self.producto,
            sucursal=self.sucursal_destino,
            tipo_movimiento='TRANSFERENCIA_ENTRADA',
            cantidad=self.cantidad
        )

        super(Transferencia, self).save(*args, **kwargs)


class MovimientoInventario(models.Model):
    TIPOS_MOVIMIENTO = [
        ('COMPRA', 'Compra'),
        ('TRANSFERENCIA_ENTRADA', 'Transferencia Entrada'),
        ('TRANSFERENCIA_SALIDA', 'Transferencia Salida'),
        ('VENTA', 'Venta'),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    tipo_movimiento = models.CharField(max_length=25, choices=TIPOS_MOVIMIENTO)
    cantidad = models.IntegerField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo_movimiento} de {self.cantidad} de {self.producto.nombre} en {self.sucursal.nombre}"