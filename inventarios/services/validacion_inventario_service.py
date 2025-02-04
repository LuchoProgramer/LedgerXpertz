from inventarios.models import Inventario
from django_tenants.utils import tenant_context

class ValidacionInventarioService:
    
    @staticmethod
    def validar_inventario(producto, presentacion, cantidad, tenant):
        """
        Valida si hay suficientes unidades en el inventario para la presentación seleccionada.
        Se asegura de ejecutarlo dentro del contexto del tenant.
        """
        if not tenant:
            print("Error: No se proporcionó un tenant válido.")
            return False

        with tenant_context(tenant):
            unidades_requeridas = presentacion.cantidad * cantidad
            inventario = Inventario.objects.filter(producto=producto, sucursal=presentacion.sucursal).first()

            if not inventario:
                print(f"No se encontró inventario para el producto {producto.nombre} en la sucursal {presentacion.sucursal.nombre}.")
                return False

            if inventario.cantidad < unidades_requeridas:
                print(f"Inventario insuficiente: Se requieren {unidades_requeridas}, pero solo hay {inventario.cantidad} disponibles.")
                return False

            return True

    @staticmethod
    def validar_stock_disponible(producto, cantidad, tenant):
        """
        Valida si hay suficiente inventario disponible para un producto específico.
        Se ejecuta dentro del contexto del tenant.
        """
        if not tenant:
            print("Error: No se proporcionó un tenant válido.")
            return False

        with tenant_context(tenant):
            inventario = Inventario.objects.filter(producto=producto).first()

            if not inventario:
                print(f"No se encontró inventario para el producto {producto.nombre}.")
                return False

            if inventario.cantidad < cantidad:
                print(f"Stock insuficiente: Se requieren {cantidad} unidades, pero solo hay {inventario.cantidad} disponibles.")
                return False

            return True
