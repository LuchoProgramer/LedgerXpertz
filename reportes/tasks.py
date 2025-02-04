from celery import shared_task
from django.utils import timezone
from reportes.models import MovimientoReporte, Reporte
from django.db.models import Sum, Q
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@shared_task
def actualizar_reporte_ventas():
    try:
        # Obtener la fecha actual
        fecha_actual = timezone.now().date()

        # Obtener los movimientos de ventas del día con optimización de consultas
        movimientos = MovimientoReporte.objects.filter(fecha=fecha_actual).select_related(
            'pago', 'venta__factura'
        )

        # Agrupar por sucursal
        sucursales = movimientos.values('sucursal_id').distinct()

        # Procesar los reportes por cada sucursal
        for sucursal_data in sucursales:
            sucursal_id = sucursal_data['sucursal_id']
            movimientos_sucursal = movimientos.filter(sucursal_id=sucursal_id)

            # Calcular los totales
            totals = movimientos_sucursal.aggregate(
                total_ventas=Sum('total_venta'),
                total_efectivo=Sum('pago__total', filter=Q(pago__descripcion__icontains='efectivo')),
                otros_metodos_pago=Sum('pago__total', filter=~Q(pago__descripcion__icontains='efectivo'))
            )

            # Valores de totales, asegurándose de que no sean None
            total_ventas = totals['total_ventas'] or 0
            total_efectivo = totals['total_efectivo'] or 0
            otros_metodos_pago = totals['otros_metodos_pago'] or 0
            total_facturas = movimientos_sucursal.values('venta__factura').distinct().count()

            # Crear o actualizar el reporte dentro de una transacción
            with transaction.atomic():
                reporte, created = Reporte.objects.get_or_create(
                    sucursal_id=sucursal_id,
                    fecha=fecha_actual,
                    defaults={
                        'total_ventas': total_ventas,
                        'total_facturas': total_facturas,
                        'total_efectivo': total_efectivo,
                        'otros_metodos_pago': otros_metodos_pago
                    }
                )

                if not created:
                    # Actualizar los valores si ya existe el reporte
                    reporte.total_ventas = total_ventas
                    reporte.total_facturas = total_facturas
                    reporte.total_efectivo = total_efectivo
                    reporte.otros_metodos_pago = otros_metodos_pago
                    reporte.save()

        logger.info(f'Reporte de ventas actualizado para la fecha {fecha_actual}')

    except Exception as e:
        logger.error(f'Error al actualizar el reporte de ventas: {e}', exc_info=True)  # Agregar traceback
        raise e  # Si prefieres propagar la excepción