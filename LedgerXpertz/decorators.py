from functools import wraps
from django.http import HttpResponseForbidden
from django_tenants.utils import tenant_context

def group_required_tenant(group_name):
    """
    Decorador para restringir el acceso según el grupo del usuario y el tenant actual,
    usando tenant_context para asegurar que se usa el esquema correcto.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Verificar si el usuario está autenticado
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Debes estar autenticado para acceder a esta vista.")
            
            # Usar tenant_context para asegurarnos de que estamos en el contexto del tenant correcto
            with tenant_context(request.tenant):
                # Verificar si el usuario pertenece al grupo adecuado
                if request.user.groups.filter(name=group_name).exists():
                    return view_func(request, *args, **kwargs)
            
            return HttpResponseForbidden("No tienes permiso para acceder a esta vista.")
        return _wrapped_view
    return decorator

# Decoradores específicos para cada grupo
def administrador_required(view_func):
    """
    Decorador para verificar si el usuario pertenece al grupo 'Administrador'.
    """
    return group_required_tenant('Administrador')(view_func)

def franquicia_required(view_func):
    """
    Decorador para verificar si el usuario pertenece al grupo 'Administrador de la franquicia'.
    """
    return group_required_tenant('Administrador de la franquicia')(view_func)

def usuario_required(view_func):
    """
    Decorador para verificar si el usuario pertenece al grupo 'Usuarios'.
    """
    return group_required_tenant('Usuarios')(view_func)
