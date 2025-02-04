from inventarios.models import Inventario
from django_tenants.utils import tenant_context

class ObtenerInventariosSucursalService:

    @staticmethod
    def obtener_inventarios(sucursal, tenant):
        """
        Obtiene los inventarios de una sucursal dentro del contexto del tenant activo
        y carga las presentaciones disponibles para cada producto.
        """
        with tenant_context(tenant):  # Asegura que la consulta se haga en el tenant correcto
            inventarios = Inventario.objects.filter(sucursal=sucursal).select_related('producto__categoria')

            # Añadir las presentaciones de cada producto sin asignarlas
            for inventario in inventarios:
                presentaciones = inventario.producto.presentaciones.all()  # Accedemos sin reasignar
                print(f"Producto: {inventario.producto.nombre}, Presentaciones: {[p.nombre_presentacion for p in presentaciones]}")

            return inventarios