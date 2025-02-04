from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from RegistroTurnos.models import RegistroTurno
from core.models import Sucursal
from .forms import RegistroTurnoForm, CustomUserCreationForm
from django.contrib.auth.decorators import user_passes_test
from django_tenants.utils import tenant_context  # Importar tenant_context
import traceback


def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


@login_required
def dashboard(request):
    usuario = request.user
    tenant = request.tenant  # Obtener el tenant actual
    print(f"Usuario: {usuario.username}, Tenant: {tenant.schema_name}")

    # Filtrar datos específicos del tenant
    with tenant_context(tenant):
        turno_activo = RegistroTurno.objects.filter(usuario=usuario, fin_turno__isnull=True).first()
        if turno_activo:
            print(f"Turno activo encontrado: {turno_activo.id} para el usuario {usuario.username}")
            if is_ajax(request):
                return JsonResponse({'success': True, 'turno_id': turno_activo.id})
            return redirect('ventas:inicio_turno', turno_id=turno_activo.id)

        sucursales_usuario = list(Sucursal.objects.filter(usuarios=usuario))
        sucursales_count = len(sucursales_usuario)
        print(f"Cantidad de sucursales asignadas al usuario {usuario.username}: {sucursales_count}")

        if sucursales_count == 0:
            print(f"Usuario {usuario.username} no tiene sucursales asignadas.")
            return redirect('sin_sucursales')

        if sucursales_count == 1:
            sucursal_unica = sucursales_usuario[0]
            form = RegistroTurnoForm(usuario=request.user, initial={'sucursal': sucursal_unica})
        else:
            form = RegistroTurnoForm(usuario=request.user)

        if request.method == 'POST':
            print(f"Usuario {usuario.username} está intentando iniciar un turno con datos POST.")
            form = RegistroTurnoForm(request.POST, usuario=request.user)
            if form.is_valid():
                try:
                    turno = form.save(commit=False)
                    turno.usuario = request.user
                    turno.inicio_turno = timezone.now()
                    turno.save()
                    print(f"Turno creado exitosamente: {turno.id} para el usuario {usuario.username}")
                    if is_ajax(request):
                        return JsonResponse({'success': True, 'turno_id': turno.id})
                    return redirect('ventas:inicio_turno', turno_id=turno.id)
                except Exception as e:
                    print(f"Error al iniciar el turno para el usuario {usuario.username}: {str(e)}")
                    if is_ajax(request):
                        return JsonResponse({'success': False, 'message': f"Error al iniciar el turno: {str(e)}"})
                    messages.error(request, f"Error al iniciar el turno: {str(e)}")
            else:
                print(f"Formulario inválido: {form.errors}")
                if is_ajax(request):
                    return JsonResponse({'success': False, 'message': "Error en el formulario.", 'errors': form.errors})
                messages.error(request, "Error en el formulario.")

    return render(request, 'registro-turnos/dashboard.html', {'form': form})


@login_required
def sin_sucursales(request):
    return render(request, 'registro-turnos/sin_sucursales.html', {
        'mensaje': "No tienes ninguna sucursal asignada. Por favor, contacta con un administrador para más información."
    })