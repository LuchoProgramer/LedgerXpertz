from ventas.models import Venta, CierreCaja, Carrito
from inventarios.models import Inventario
from RegistroTurnos.models import RegistroTurno
from facturacion.models import Factura
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from inventarios.services.validacion_inventario_service import ValidacionInventarioService
from django_tenants.utils import tenant_context
from core.models import Producto


class VentaService:
    
    @staticmethod
    @transaction.atomic
    def registrar_venta(turno_activo, producto, cantidad, factura, presentacion):
        print("Iniciando el registro de la venta...")

        if not presentacion:
            raise ValueError(f"No se encontró una presentación para el producto {producto.nombre}")

        # Calcular el total de la venta usando la presentación seleccionada
        precio_unitario = presentacion.precio  # El precio unitario de la presentación seleccionada
        total_venta = cantidad * precio_unitario  # Precio total de la venta
        print(f"Total de la venta calculado: {total_venta} para {cantidad} unidades de {presentacion.nombre_presentacion} del producto {producto.nombre}")

        # Usar tenant_context para asegurar que la operación se realiza en el contexto del tenant actual
        with tenant_context(turno_activo.sucursal.empresa):
            try:
                venta = Venta.objects.create(
                    turno=turno_activo,
                    sucursal=turno_activo.sucursal,
                    usuario=turno_activo.usuario,
                    producto=producto,
                    cantidad=cantidad,  # Usar cantidad total en unidades
                    precio_unitario=precio_unitario,
                    total_venta=total_venta,
                    factura=factura,
                    fecha=timezone.now(),
                )
                print(f"Venta registrada exitosamente con ID: {venta.id} para el producto {producto.nombre}")
            except Exception as e:
                print(f"Error al registrar la venta: {str(e)}")
                raise ValueError(f"Error al registrar la venta: {str(e)}")

        return venta


    @staticmethod
    @transaction.atomic
    def finalizar_venta(turno):
        print(f"Iniciando el proceso de finalizar venta para el turno: {turno.id}")
        
        with tenant_context(turno.sucursal.empresa):
            carrito_items = Carrito.objects.filter(turno=turno).select_related('presentacion', 'producto')
            print(f"Carrito para el turno {turno.id}, productos en el carrito: {carrito_items.count()}")

            if not carrito_items.exists():
                print("El carrito está vacío. No se puede finalizar la venta.")
                raise ValueError("El carrito está vacío. No se puede finalizar la venta.")

            total_sin_impuestos = Decimal('0.00')
            total_con_impuestos = Decimal('0.00')
            errores = []

            for item in carrito_items:
                producto = item.producto
                presentacion = item.presentacion
                cantidad = item.cantidad

                print(f"Procesando producto: {producto.nombre}, cantidad de presentaciones: {cantidad}, presentación: {presentacion.nombre_presentacion}")

                # Validar inventario utilizando el servicio de validación dentro del contexto del tenant
                if not ValidacionInventarioService.validar_inventario(producto, presentacion, cantidad):
                    print(f"Error: No hay suficiente inventario para {producto.nombre}.")
                    errores.append(f"No hay suficiente inventario para {producto.nombre}.")
                    continue  # Pasar al siguiente item si hay un error

                try:
                    # Registrar la venta con la presentación seleccionada
                    total_item = item.subtotal()  # El subtotal ya incluye el precio unitario * cantidad
                    nueva_venta = VentaService.registrar_venta(turno, producto, cantidad * presentacion.cantidad, factura=None, presentacion=presentacion)
                    print(f"Venta creada: {nueva_venta.id} para el producto: {producto.nombre}")
                except Exception as e:
                    print(f"Error al crear la venta para {producto.nombre}: {str(e)}")
                    errores.append(f"No se pudo registrar la venta para {producto.nombre}")

                total_sin_impuestos += total_item
                total_con_impuestos += total_item * Decimal('1.12')  # Aplicar IVA

            if errores:
                print(f"Errores al registrar ventas: {'; '.join(errores)}")
                raise ValueError("\n".join(errores))

            # Crear la factura dentro del tenant
            factura = Factura.objects.create(
                sucursal=turno.sucursal,
                cliente=turno.usuario.cliente,
                usuario=turno.usuario,
                total_sin_impuestos=total_sin_impuestos,
                total_con_impuestos=total_con_impuestos,
                estado='AUTORIZADA',
                turno=turno,
            )
            print(f"Factura creada exitosamente con ID: {factura.id} para el turno {turno.id}")

            carrito_items.delete()  # Vaciar el carrito después de completar la venta
            print("Carrito vaciado después de la venta.")

        return factura


class TurnoService:
    @staticmethod
    @transaction.atomic
    def cerrar_turno(turno, cierre_form_data):
        try:
            with tenant_context(turno.sucursal.empresa):
                cierre_caja = CierreCaja.objects.create(
                    usuario=turno.usuario,
                    sucursal=turno.sucursal,
                    fecha_cierre=timezone.now(),
                    efectivo_total=cierre_form_data.get('efectivo_total'),
                    tarjeta_total=cierre_form_data.get('tarjeta_total'),
                    transferencia_total=cierre_form_data.get('transferencia_total'),
                    salidas_caja=cierre_form_data.get('salidas_caja', 0),
                )
                turno.fin_turno = timezone.now()
                turno.save()

            return cierre_caja

        except Exception as e:
            raise ValueError(f"Error al cerrar el turno: {str(e)}")