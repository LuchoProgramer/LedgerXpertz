from ventas.models import Venta
from RegistroTurnos.models import RegistroTurno
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django_tenants.utils import tenant_context

def generar_reporte_ventas_por_turno(turno_id, tenant):
    # Usamos tenant_context para garantizar que las consultas sean seguras dentro del esquema del tenant
    with tenant_context(tenant):
        # Obtener el turno o lanzar una excepción 404 si no se encuentra
        turno = get_object_or_404(RegistroTurno, id=turno_id)

        # Obtener todas las ventas asociadas al turno
        ventas = turno.ventas.all()

        # Calcular el total de ventas, asegurándose de que no sea None
        total_ventas = ventas.aggregate(total=Sum('total_venta'))['total'] or 0

    return ventas, total_ventas
