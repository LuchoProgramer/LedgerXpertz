from inventarios.models import Inventario
from django.core.exceptions import ValidationError
from django_tenants.utils import tenant_context

class AjusteInventarioService:

    @staticmethod
    def ajustar_inventario(producto, presentacion, cantidad, tenant):
        """
        Ajusta el inventario según la presentación seleccionada y la cantidad solicitada.
        Se asegura de ejecutarlo dentro del contexto del tenant.
        """
        with tenant_context(tenant):
            unidades_a_descontar = presentacion.cantidad * cantidad

            inventario = Inventario.objects.filter(producto=producto, sucursal=presentacion.sucursal).first()

            if not inventario:
                raise ValidationError("No se encontró inventario para este producto en la sucursal seleccionada.")
            
            if inventario.cantidad < unidades_a_descontar:
                raise ValidationError("Inventario insuficiente para esta cantidad.")

            # Actualizar el inventario
            inventario.cantidad -= unidades_a_descontar
            inventario.save()