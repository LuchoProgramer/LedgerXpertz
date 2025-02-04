from inventarios.models import Inventario, MovimientoInventario
from django_tenants.utils import tenant_context

class MovimientoInventarioService:

    @staticmethod
    def registrar_movimiento(producto, sucursal, tipo_movimiento, cantidad, tenant):
        """
        Registra un movimiento de inventario sin modificar las cantidades,
        asegurando que la operación ocurra dentro del contexto del tenant activo.
        """
        with tenant_context(tenant):  # Asegura que el movimiento se registre en el tenant correcto
            MovimientoInventario.objects.create(
                producto=producto,
                sucursal=sucursal,
                tipo_movimiento=tipo_movimiento,
                cantidad=cantidad
            )
            print(f"Movimiento de inventario registrado para el producto {producto.nombre}, cantidad ajustada: {cantidad}")