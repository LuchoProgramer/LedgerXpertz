from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import connection
from django_tenants.utils import tenant_context
from .models import RegistroTurno

def asignar_turno(usuario, sucursal, inicio_turno=None):
    """
    Asigna un turno para un usuario en una sucursal específica.

    :param usuario: Usuario al que se le asigna el turno
    :param sucursal: La sucursal donde se inicia el turno
    :param inicio_turno: Fecha y hora opcional para el inicio del turno
    :return: El objeto RegistroTurno recién creado
    """
    # Obtener el tenant activo
    current_tenant = connection.tenant

    with tenant_context(current_tenant):  # Ejecutar dentro del contexto del tenant activo
        # Verificar si ya tiene un turno activo
        turno_activo = RegistroTurno.turno_activo(usuario)
        if turno_activo:
            raise ValidationError('El usuario ya tiene un turno activo.')

        # Crear el turno
        if not inicio_turno:
            inicio_turno = timezone.now()

        nuevo_turno = RegistroTurno(
            usuario=usuario,
            sucursal=sucursal,
            inicio_turno=inicio_turno
        )

        # Validar el turno
        nuevo_turno.full_clean()

        # Guardar el turno
        nuevo_turno.save()

    return nuevo_turno
