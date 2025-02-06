from RegistroTurnos.models import RegistroTurno
from django.db import connection
from django_tenants.utils import tenant_context

def turno_context(request):
    turno_activo = None
    sucursal_activa = None

    if request.user.is_authenticated:
        current_tenant = connection.tenant
        with tenant_context(current_tenant):
            turno_activo = RegistroTurno.obtener_turno_activo(request.user)
            if turno_activo:
                sucursal_activa = turno_activo.sucursal

    return {'turno_activo': turno_activo, 'sucursal_activa': sucursal_activa}
