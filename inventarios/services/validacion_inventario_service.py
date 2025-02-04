from inventarios.models import Inventario
from django_tenants.utils import tenant_context
from empresas.models import Empresa

class ValidacionInventarioService:
    
    @staticmethod
    def validar_inventario(tenant, producto, presentacion, cantidad):
        """
        Valida si hay suficientes unidades en el inventario para la presentación seleccionada.
        Se asegura de ejecutarlo dentro del contexto del tenant.
        """
        print(f"✅ Entrando a validar_inventario con tenant: {tenant.schema_name}, Producto: {producto.nombre}, Presentación: {presentacion.nombre_presentacion}, Cantidad: {cantidad}")

        if not isinstance(tenant, Empresa):  # Validar que sea una instancia de Empresa
            print("❌ Error: Tenant no es válido.")
            return False

        with tenant_context(tenant):
            print(f"🔄 Cambiando al esquema del tenant: {tenant.schema_name}")

            unidades_requeridas = presentacion.cantidad * cantidad
            print(f"📦 Unidades requeridas: {unidades_requeridas}")

            inventario = Inventario.objects.filter(producto=producto, sucursal=presentacion.sucursal).first()
            print(f"🔍 Inventario encontrado: {inventario}")

            if not inventario:
                print(f"❌ No se encontró inventario para el producto {producto.nombre} en la sucursal {presentacion.sucursal.nombre}.")
                return False

            if inventario.cantidad < unidades_requeridas:
                print(f"❌ Inventario insuficiente: Se requieren {unidades_requeridas}, pero solo hay {inventario.cantidad} disponibles.")
                return False

            print("✅ Inventario suficiente, producto puede ser agregado al carrito.")
            return True


    @staticmethod
    def validar_stock_disponible(tenant, producto, cantidad):
        """
        Valida si hay suficiente inventario disponible para un producto específico.
        Se ejecuta dentro del contexto del tenant.
        """
        if not isinstance(tenant, Empresa):  # Asegurar que tenant es válido
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