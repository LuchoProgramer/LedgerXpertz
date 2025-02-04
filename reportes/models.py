from django.db import models
from RegistroTurnos.models import RegistroTurno


class Reporte(models.Model):
    turno = models.ForeignKey('RegistroTurnos.RegistroTurno', on_delete=models.CASCADE, related_name='reportes', null=True, blank=True)
    sucursal = models.ForeignKey('core.Sucursal', on_delete=models.CASCADE)
    total_ventas = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_facturas = models.IntegerField(default=0)
    total_efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    otros_metodos_pago = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fecha = models.DateField()  # Eliminamos auto_now_add para mayor control
    
    def __str__(self):
        return f'Reporte de {self.sucursal} en el turno {self.turno}'

    class Meta:
        ordering = ['fecha']



class MovimientoReporte(models.Model):
    venta = models.ForeignKey('ventas.Venta', on_delete=models.CASCADE)  # Usamos una cadena de texto
    turno = models.ForeignKey('RegistroTurnos.RegistroTurno', on_delete=models.CASCADE)
    sucursal = models.ForeignKey('core.Sucursal', on_delete=models.CASCADE)
    pago = models.ForeignKey('facturacion.Pago', on_delete=models.CASCADE, null=True, blank=True)  # Usamos una cadena de texto
    total_venta = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Movimiento de Reporte: Venta {self.venta.id} - Sucursal {self.sucursal.nombre}"