from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

class RegistroTurno(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    sucursal = models.ForeignKey('core.Sucursal', on_delete=models.CASCADE)
    inicio_turno = models.DateTimeField()
    fin_turno = models.DateTimeField(null=True, blank=True)
    total_ventas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    otros_metodos_pago = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @classmethod
    def obtener_turno_activo(cls, usuario):
        """
        Retorna el turno activo del usuario si existe, o None si no hay uno activo.
        Si hay más de un turno activo, lanza un error.
        """
        turnos_activos = cls.objects.filter(usuario=usuario, fin_turno__isnull=True)
        if turnos_activos.count() > 1:
            raise ValidationError('El usuario tiene múltiples turnos activos.')
        return turnos_activos.first()

    def cerrar_turno(self, efectivo_total, tarjeta_total, transferencia_total, salidas_caja):
        """
        Cierra el turno actual y actualiza los registros financieros correspondientes.
        """
        from ventas.models import CierreCaja
        from reportes.models import Reporte
        from decimal import Decimal

        if self.fin_turno:
            raise ValidationError("Este turno ya está cerrado.")

        try:
            with transaction.atomic():
                self.fin_turno = timezone.now()
                self.total_efectivo = efectivo_total
                self.otros_metodos_pago = tarjeta_total + transferencia_total
                self.save()

                # Crear el cierre de caja
                CierreCaja.objects.create(
                    usuario=self.usuario,
                    sucursal=self.sucursal,
                    efectivo_total=efectivo_total,
                    tarjeta_total=tarjeta_total,
                    transferencia_total=transferencia_total,
                    salidas_caja=salidas_caja,
                    fecha_cierre=self.fin_turno
                )

                # Actualizar el reporte
                reporte, _ = Reporte.objects.get_or_create(
                    turno=self,
                    sucursal=self.sucursal,
                    fecha=self.inicio_turno.date()
                )
                reporte.total_efectivo += Decimal(efectivo_total)
                reporte.otros_metodos_pago += Decimal(tarjeta_total + transferencia_total)
                reporte.save()

                logger.info(f"Reporte del turno actualizado: {reporte.id}")

        except Exception as e:
            logger.error(f"Error al cerrar el turno: {str(e)}")
            raise e

    def clean(self):
        """
        Validaciones antes de guardar el turno.
        """
        if self.fin_turno and self.fin_turno <= self.inicio_turno:
            raise ValidationError('El fin del turno debe ser posterior al inicio.')

        if hasattr(self, 'usuario') and self.usuario:
            if not self.fin_turno and RegistroTurno.obtener_turno_activo(self.usuario):
                raise ValidationError('El usuario ya tiene un turno activo.')

        super(RegistroTurno, self).clean()

    def __str__(self):
        return f"Turno de {self.usuario.username} en {self.sucursal.nombre} - Inicio: {self.inicio_turno}"