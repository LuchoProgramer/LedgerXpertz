from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from ventas.models import Venta
from reportes.models import Reporte
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Venta)
def actualizar_reporte_ventas(sender, instance, created, **kwargs):
    if created:
        logger.info(f"Señal disparada para la venta con ID: {instance.id}")
        fecha_venta = instance.fecha.date()
        logger.info(f"Fecha de la venta: {fecha_venta}")

        try:
            with transaction.atomic():
                # Obtener o crear el reporte para la sucursal y fecha de la venta
                reporte, creado = Reporte.objects.get_or_create(
                    turno=instance.turno,
                    sucursal=instance.sucursal,
                    fecha=fecha_venta
                )

                logger.info(f"Reporte {'creado' if creado else 'actualizado'} para la fecha {fecha_venta} y sucursal {instance.sucursal.nombre}")

                # Inicializar los valores como Decimal
                total_efectivo = Decimal('0.00')
                total_otros_metodos = Decimal('0.00')

                # Si la venta tiene factura y pagos asociados, procesarlos
                if instance.factura and instance.factura.pagos.exists():
                    for pago in instance.factura.pagos.all():
                        if pago.codigo_sri == '01':  # Efectivo
                            total_efectivo += Decimal(pago.total)  # Convertir siempre a Decimal
                        else:
                            total_otros_metodos += Decimal(pago.total)  # Convertir siempre a Decimal

                    logger.info(f"Total efectivo: {total_efectivo}, Otros métodos de pago: {total_otros_metodos}")

                    # Actualizar los valores del reporte
                    reporte.total_efectivo = Decimal(reporte.total_efectivo) + total_efectivo
                    reporte.otros_metodos_pago = Decimal(reporte.otros_metodos_pago) + total_otros_metodos
                    reporte.total_facturas = int(reporte.total_facturas) + 1  # Asegurarse de que las facturas sean un entero
                    reporte.save()

                    logger.info(f"Reporte actualizado: {reporte.id} - Total efectivo: {reporte.total_efectivo}, Total facturas: {reporte.total_facturas}")
                else:
                    logger.warning(f"La venta con ID {instance.id} no tiene pagos asociados a la factura.")
        except Exception as e:
            logger.error(f"Error al actualizar el reporte de ventas para la venta con ID {instance.id}: {e}", exc_info=True)
            raise e  # Propagar la excepción si es necesario