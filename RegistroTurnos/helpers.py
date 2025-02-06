from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import connection
from django_tenants.utils import tenant_context
from RegistroTurnos.models import RegistroTurno

def asignar_turno(usuario, sucursal, inicio_turno=None):
    """
    Asigna un turno para un usuario en una sucursal específica.
    """
    current_tenant = connection.tenant

    with tenant_context(current_tenant):
        turno_activo = RegistroTurno.obtener_turno_activo(usuario)
        if turno_activo:
            raise ValidationError('El usuario ya tiene un turno activo.')

        if not inicio_turno:
            inicio_turno = timezone.now()

        nuevo_turno = RegistroTurno(
            usuario=usuario,
            sucursal=sucursal,
            inicio_turno=inicio_turno
        )
        nuevo_turno.full_clean()
        nuevo_turno.save()

    return nuevo_turno