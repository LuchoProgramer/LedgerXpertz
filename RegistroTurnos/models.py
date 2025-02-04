from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

class RegistroTurno(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)  # Relaciona cada turno con un usuario
    sucursal = models.ForeignKey('core.Sucursal', on_delete=models.CASCADE)  # Relaciona con una sucursal
    inicio_turno = models.DateTimeField()  # Fecha y hora del inicio del turno
    fin_turno = models.DateTimeField(null=True, blank=True)  # Fecha y hora del cierre del turno
    total_ventas = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Total ventas durante el turno
    total_efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Total en efectivo
    otros_metodos_pago = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Total otros pagos (tarjeta, etc.)

    def cerrar_turno(self, efectivo_total, tarjeta_total, transferencia_total, salidas_caja):
        """
        Cierra el turno y realiza todas las actualizaciones necesarias:
        - Asigna la fecha de cierre del turno
        - Crea el registro de CierreCaja
        - Actualiza los totales en el Reporte del turno
        """
        from ventas.models import CierreCaja
        from reportes.models import Reporte
        from decimal import Decimal

        # Verificar si el turno ya ha sido cerrado
        if self.fin_turno:
            raise ValidationError("Este turno ya está cerrado.")

        try:
            with transaction.atomic():  # Envolver todo en una transacción atómica para garantizar consistencia
                # Actualizar el fin del turno y los totales
                self.fin_turno = timezone.now()
                self.total_efectivo = efectivo_total
                self.otros_metodos_pago = tarjeta_total + transferencia_total
                self.save()

                # Crear el registro de cierre de caja
                CierreCaja.objects.create(
                    usuario=self.usuario,
                    sucursal=self.sucursal,
                    efectivo_total=efectivo_total,
                    tarjeta_total=tarjeta_total,
                    transferencia_total=transferencia_total,
                    salidas_caja=salidas_caja,
                    fecha_cierre=self.fin_turno
                )

                # Obtener o crear el reporte del turno
                reporte, creado = Reporte.objects.get_or_create(
                    turno=self,
                    sucursal=self.sucursal,
                    fecha=self.inicio_turno.date()
                )

                # Actualizar los totales en el reporte
                reporte.total_efectivo += Decimal(efectivo_total)
                reporte.otros_metodos_pago += Decimal(tarjeta_total + transferencia_total)
                reporte.save()

                logger.info(f"Reporte del turno actualizado: {reporte.id} - Total Efectivo: {reporte.total_efectivo} - Otros Métodos: {reporte.otros_metodos_pago}")

        except Exception as e:
            logger.error(f"Error al cerrar el turno: {str(e)}")
            raise e  # Rethrow para que se maneje en la vista o capa superior

    @classmethod
    def turno_activo(cls, usuario):
        """
        Verifica si el usuario tiene algún turno activo.
        Si tiene más de un turno activo, lanza un error.
        """
        turnos_activos = cls.objects.filter(usuario=usuario, fin_turno__isnull=True)
        if turnos_activos.count() > 1:
            raise ValidationError('El usuario tiene múltiples turnos activos.')
        return turnos_activos.first()

    def clean(self):
        # Validar que el fin del turno sea posterior al inicio
        if self.fin_turno and self.fin_turno <= self.inicio_turno:
            raise ValidationError('El fin del turno debe ser posterior al inicio.')

        # Solo validar el turno activo si el usuario ya está asignado
        if hasattr(self, 'usuario') and self.usuario:
            if not self.fin_turno and RegistroTurno.turno_activo(self.usuario):
                raise ValidationError('El usuario ya tiene un turno activo.')

        # Llamar al clean de la clase base
        super(RegistroTurno, self).clean()


    def __str__(self):
        """
        Devuelve una representación legible del turno, útil para interfaces y registros
        """
        return f"Turno de {self.usuario.username} en {self.sucursal.nombre} - Inicio: {self.inicio_turno}"