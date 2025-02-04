from django.db import models, transaction
from inventarios.models import Inventario, MovimientoInventario
from django.db.models import Sum
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.apps import apps

# Importaciones específicas
from inventarios.models import Inventario, MovimientoInventario
from core.models import Sucursal, Presentacion
from facturacion.models import Pago, Factura
from django.contrib.auth.models import User  



class Venta(models.Model):
    # Campos principales
    turno = models.ForeignKey(
        'RegistroTurnos.RegistroTurno',
        on_delete=models.CASCADE,
        related_name='ventas'
    )
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    usuario = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    producto = models.ForeignKey('core.Producto', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()  # Asegura valores positivos
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total_venta = models.DecimalField(
        max_digits=10, decimal_places=2, editable=False
    )
    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        related_name='ventas',
    )
    fecha = models.DateTimeField(auto_now_add=True)
    metodo_pago = models.CharField(
        max_length=2,
        choices=Pago.METODOS_PAGO_SRI,
        default='01',
        help_text="Método de pago utilizado para la venta",
    )

    def clean(self):
        """
        Validaciones personalizadas antes de guardar.
        """
        if self.cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor que cero.')
        if self.precio_unitario <= 0:
            raise ValidationError('El precio unitario debe ser mayor que cero.')

    def calcular_total_venta(self):
        """
        Calcula el total de la venta con precisión decimal.
        """
        return (self.cantidad * self.precio_unitario).quantize(Decimal('0.01'))

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Guarda el modelo asegurando validaciones y procesos adicionales.
        """
        # Validar antes de guardar
        self.full_clean()

        # Calcular el total de la venta
        self.total_venta = self.calcular_total_venta()

        # Guardar la venta
        super().save(*args, **kwargs)

        # Crear un movimiento de reporte
        self.crear_movimiento_reporte()

    def crear_movimiento_reporte(self):
        """
        Crea un registro en el modelo MovimientoReporte.
        """
        MovimientoReporte = apps.get_model('reportes', 'MovimientoReporte')

        # Obtener el primer pago asociado a la factura
        pago_asociado = Pago.objects.filter(factura=self.factura).first()

        # Crear movimiento de reporte
        movimiento = MovimientoReporte.objects.create(
            venta=self,
            turno=self.turno,
            sucursal=self.sucursal,
            total_venta=self.total_venta,
            pago=pago_asociado,
        )

        # Mensaje para depuración
        print(f"Movimiento de reporte creado exitosamente con ID: {movimiento.id}")

    def __str__(self):
        """
        Representación del modelo como cadena.
        """
        return f"Venta de {self.producto.nombre} en {self.sucursal.nombre} - {self.cantidad} unidades - Total: {self.total_venta}"


#Cierra de caja
class CierreCaja(models.Model):
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    efectivo_total = models.DecimalField(max_digits=10, decimal_places=2)
    tarjeta_total = models.DecimalField(max_digits=10, decimal_places=2)
    transferencia_total = models.DecimalField(max_digits=10, decimal_places=2)
    salidas_caja = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_cierre = models.DateTimeField(auto_now_add=True)
    motivo_salida = models.CharField(max_length=255, blank=True, null=True)

    def calcular_total_neto(self):
        return (self.efectivo_total + self.tarjeta_total + self.transferencia_total) - self.salidas_caja

    @transaction.atomic
    def verificar_montos(self):
        from ventas.models import Venta  # Evitar ciclos de importación

        # Filtrar las ventas para la fecha, sucursal y empleado específicos
        ventas = Venta.objects.filter(
            fecha__date=self.fecha_cierre.date(),
            sucursal=self.sucursal,
            usuario=self.usuario
        )

        # Realizar agregaciones para calcular los totales directamente en la base de datos
        totales = ventas.values('metodo_pago').annotate(total=Sum('total_venta'))

        # Obtener los totales por cada método de pago o asignar 0 si no existen
        total_ventas_efectivo = Decimal(next((item['total'] for item in totales if item['metodo_pago'] == 'Efectivo'), 0))
        total_ventas_tarjeta = Decimal(next((item['total'] for item in totales if item['metodo_pago'] == 'Tarjeta'), 0))
        total_ventas_transferencia = Decimal(next((item['total'] for item in totales if item['metodo_pago'] == 'Transferencia'), 0))

        errores = []
        if total_ventas_efectivo != self.efectivo_total:
            errores.append(f"Discrepancia en efectivo: {total_ventas_efectivo} esperado, {self.efectivo_total} registrado.")
        if total_ventas_tarjeta != self.tarjeta_total:
            errores.append(f"Discrepancia en tarjeta: {total_ventas_tarjeta} esperado, {self.tarjeta_total} registrado.")
        if total_ventas_transferencia != self.transferencia_total:
            errores.append(f"Discrepancia en transferencias: {total_ventas_transferencia} esperado, {self.transferencia_total} registrado.")

        return errores if errores else "Los montos coinciden."
    


class Carrito(models.Model):
    turno = models.ForeignKey('RegistroTurnos.RegistroTurno', on_delete=models.CASCADE, related_name='carritos')
    producto = models.ForeignKey('core.Producto', on_delete=models.CASCADE)
    presentacion = models.ForeignKey(Presentacion, on_delete=models.CASCADE)  # Relación con Presentación
    cantidad = models.PositiveIntegerField(default=1)
    agregado_el = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Validar que la cantidad sea positiva
        if self.cantidad <= 0:
            raise ValidationError('La cantidad del producto debe ser mayor que cero.')

        # Verificar que haya suficiente inventario para la presentación seleccionada
        inventario = Inventario.objects.filter(producto=self.producto, sucursal=self.turno.sucursal).first()
        total_unidades = self.presentacion.cantidad * self.cantidad
        if not inventario or inventario.cantidad < total_unidades:
            raise ValidationError(f'No hay suficiente stock para {self.producto.nombre} en la presentación {self.presentacion.nombre_presentacion}. Disponibles: {inventario.cantidad if inventario else 0}')

        super().clean()

    def subtotal(self):
        # Calcular subtotal con el precio de la presentación, con precisión de dos decimales
        return (self.presentacion.precio * self.cantidad).quantize(Decimal('0.01'))

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} ({self.presentacion.nombre_presentacion}) en {self.turno.sucursal.nombre}"