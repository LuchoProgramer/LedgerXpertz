from RegistroTurnos.models import RegistroTurno
from django.db import connection
from django_tenants.utils import tenant_context

def turno_context(request):
    # Inicializar turno activo y sucursal como None
    turno_activo = None
    sucursal_activa = None

    # Verificar si el usuario está autenticado
    if request.user.is_authenticated:
        current_tenant = connection.tenant  # Obtener el tenant activo
        with tenant_context(current_tenant):  # Usar el contexto del tenant activo
            # Intentar recuperar un registro de turno activo para el usuario actual
            turno_activo = RegistroTurno.objects.filter(usuario=request.user, fin_turno__isnull=True).first()
            if turno_activo:
                # Si hay un turno activo, asociar la sucursal del turno
                sucursal_activa = turno_activo.sucursal

    # Devolver el turno activo y la sucursal activa en el contexto
    return {'turno_activo': turno_activo, 'sucursal_activa': sucursal_activa}