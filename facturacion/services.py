from decimal import Decimal, ROUND_HALF_UP
from .models import Factura, DetalleFactura, Impuesto  # Asegúrate de importar el modelo Impuesto
from inventarios.models import Inventario, MovimientoInventario
from django.core.exceptions import ValidationError
from .utils.xml_generator import generar_xml_para_sri
from .utils.clave_acceso import generar_clave_acceso
from django.db import transaction, IntegrityError
from facturacion.models import Cliente, Pago
from RegistroTurnos.models import RegistroTurno
from facturacion.pdf.factura_pdf import generar_pdf_factura
import os
from django.conf import settings
from inventarios.services.validacion_inventario_service import ValidacionInventarioService
from inventarios.services.ajuste_inventario_service import AjusteInventarioService
from core.models import Empresa  # Cambia RazonSocial por Empresa
from django_tenants.utils import tenant_context  # Importamos tenant_context para asegurar el contexto del tenant
from facturacion.pdf.generar_pdf_cotizacion import generar_pdf_cotizacion


def obtener_valor_base_iva(precio_con_iva, porcentaje_iva):
    precio_con_iva = Decimal(precio_con_iva)
    porcentaje_iva = Decimal(porcentaje_iva)

    valor_base = precio_con_iva / (Decimal('1') + (porcentaje_iva / Decimal('100')))
    valor_iva = precio_con_iva - valor_base
    return valor_base, valor_iva

def crear_factura(cliente, sucursal, usuario, carrito_items):
    print("Iniciando la creación de la factura...")

    iva = Impuesto.objects.filter(codigo_impuesto='2', activo=True).first()
    porcentaje_iva = Decimal(iva.porcentaje) if iva else Decimal('0.00')

    total_sin_impuestos = Decimal('0.00')
    total_iva = Decimal('0.00')
    total_con_impuestos = Decimal('0.00')

    try:
        with transaction.atomic():
            for item in carrito_items:
                print(f"Procesando producto {item.producto.nombre}...")

                presentacion = item.presentacion
                cantidad_paquetes = item.cantidad

                valor_base, valor_iva = obtener_valor_base_iva(presentacion.precio, porcentaje_iva)

                subtotal_item = valor_base * cantidad_paquetes
                iva_item = valor_iva * cantidad_paquetes

                total_sin_impuestos += subtotal_item
                total_iva += iva_item
                total_con_impuestos += subtotal_item + iva_item

            print("Iniciando transacción para crear la factura y los detalles...")

            # Aquí es donde aplicamos el contexto del tenant
            with tenant_context(sucursal.tenant):  # Establecemos el contexto del tenant
                sucursal.incrementar_secuencial()
                sucursal.save()

                codigo_establecimiento = int(sucursal.codigo_establecimiento)
                punto_emision = int(sucursal.punto_emision)
                secuencial = f"{int(sucursal.secuencial_actual):09d}"
                numero_autorizacion = f"{codigo_establecimiento:03d} {punto_emision:03d} {secuencial}"

                factura = Factura.objects.create(
                    sucursal=sucursal,
                    razon_social=sucursal.razon_social,  # Campo ajustado
                    cliente=cliente,
                    usuario=usuario,
                    numero_autorizacion=numero_autorizacion,
                    total_sin_impuestos=total_sin_impuestos.quantize(Decimal('0.01')),
                    valor_iva=total_iva.quantize(Decimal('0.01')),
                    total_con_impuestos=total_con_impuestos.quantize(Decimal('0.01')),
                    estado='EN_PROCESO',
                    es_cotizacion=False
                )
                print(f"Factura creada con número de autorización {factura.numero_autorizacion}...")

                # Crear los detalles de la factura dentro del contexto del tenant
                for item in carrito_items:
                    presentacion = item.presentacion
                    cantidad_paquetes = item.cantidad

                    valor_base, valor_iva = obtener_valor_base_iva(presentacion.precio, porcentaje_iva)
                    subtotal_item = valor_base * cantidad_paquetes
                    iva_item = valor_iva * cantidad_paquetes
                    total_item = subtotal_item + iva_item

                    print(f"Valores de detalle: cantidad={cantidad_paquetes}, precio_unitario={presentacion.precio}, subtotal={subtotal_item}, total={total_item}")

                    detalle = DetalleFactura.objects.create(
                        factura=factura,
                        producto=item.producto,
                        presentacion=presentacion,
                        cantidad=cantidad_paquetes * presentacion.cantidad,
                        precio_unitario=presentacion.precio,
                        subtotal=subtotal_item.quantize(Decimal('0.01')),
                        descuento=0,
                        total=total_item.quantize(Decimal('0.01')),
                        valor_iva=iva_item.quantize(Decimal('0.01'))
                    )
                    print(f"Detalle creado: {detalle}")

                if not factura.detalles.exists():
                    print("Error: La factura no tiene detalles asociados.")
                    raise ValidationError("La factura no tiene detalles asociados.")

                # Ajustar inventario después de la creación de la factura dentro del contexto del tenant
                for item in carrito_items:
                    AjusteInventarioService.ajustar_inventario(item.producto, item.presentacion, item.cantidad)

                print(f"Factura {factura.numero_autorizacion} completada con {factura.detalles.count()} detalles.")
                return factura

    except Exception as e:
        print(f"Error general en la transacción: {e}")
        raise e



def obtener_o_crear_cliente(cliente_id, identificacion, data_cliente):
    try:
        if cliente_id:
            cliente = Cliente.objects.get(id=cliente_id)
        else:
            cliente, created = Cliente.objects.get_or_create(
                identificacion=identificacion,
                defaults=data_cliente
            )
            if not created and not cliente.razon_social:
                raise ValidationError("Cliente incompleto. Por favor revisa los datos ingresados.")
        return cliente
    except Cliente.DoesNotExist:
        raise ValidationError("Cliente no encontrado.")

def verificar_turno_activo(usuario):
    turno_activo = RegistroTurno.objects.filter(usuario=usuario, fin_turno__isnull=True).first()
    if not turno_activo:
        raise ValidationError("No tienes un turno activo. Por favor inicia un turno.")
    return turno_activo

def asignar_pagos_a_factura(factura, metodos_pago, montos_pago):
    metodo_descripciones = {
        '01': 'Efectivo',
        '16': 'Tarjeta de Débito',
        '19': 'Tarjeta de Crédito',
        '20': 'Transferencias',
        '17': 'Dinero Electrónico'
    }

    for metodo_pago, monto_pago in zip(metodos_pago, montos_pago):
        descripcion = metodo_descripciones.get(metodo_pago, 'Método de Pago Desconocido')
        Pago.objects.create(
            factura=factura,
            codigo_sri=metodo_pago,
            total=Decimal(monto_pago),
            descripcion=f"Pago con {descripcion}"
        )

def generar_pdf_factura_y_guardar(factura):
    nombre_archivo = f"factura_{factura.numero_autorizacion}.pdf"
    ruta_pdf = os.path.join(settings.MEDIA_ROOT, nombre_archivo)
    generar_pdf_factura(factura, ruta_pdf)
    return f"/media/{nombre_archivo}"



from facturacion.models import Cotizacion, DetalleCotizacion  # Importa los modelos correctos
from inventarios.services.ajuste_inventario_service import AjusteInventarioService  # Importamos el ajuste de inventario

def crear_cotizacion(cliente, sucursal, usuario, carrito_items):
    print("Iniciando la creación de la cotización...")

    iva = Impuesto.objects.filter(codigo_impuesto='2', activo=True).first()
    porcentaje_iva = Decimal(iva.porcentaje) if iva else Decimal('0.00')

    total_sin_impuestos = Decimal('0.00')
    total_iva = Decimal('0.00')
    total_con_impuestos = Decimal('0.00')

    try:
        with transaction.atomic():
            for item in carrito_items:
                print(f"Procesando producto {item.producto.nombre}...")

                presentacion = item.presentacion
                cantidad_paquetes = item.cantidad

                valor_base, valor_iva = obtener_valor_base_iva(presentacion.precio, porcentaje_iva)

                subtotal_item = valor_base * cantidad_paquetes
                iva_item = valor_iva * cantidad_paquetes

                total_sin_impuestos += subtotal_item
                total_iva += iva_item
                total_con_impuestos += subtotal_item + iva_item

            print("Iniciando transacción para crear la cotización y los detalles...")

            # Aplicar el contexto del tenant
            with tenant_context(sucursal.tenant):  
                sucursal.incrementar_secuencial()
                sucursal.save()

                codigo_establecimiento = int(sucursal.codigo_establecimiento)
                punto_emision = int(sucursal.punto_emision)
                secuencial = f"{int(sucursal.secuencial_actual):09d}"
                numero_cotizacion = f"COT-{codigo_establecimiento:03d}{punto_emision:03d}{secuencial}"

                cotizacion = Cotizacion.objects.create(
                    sucursal=sucursal,
                    razon_social=sucursal.razon_social,  # Campo ajustado
                    cliente=cliente,
                    usuario=usuario,
                    numero_cotizacion=numero_cotizacion,
                    total_sin_impuestos=total_sin_impuestos.quantize(Decimal('0.01')),
                    valor_iva=total_iva.quantize(Decimal('0.01')),
                    total_con_impuestos=total_con_impuestos.quantize(Decimal('0.01')),
                    estado='PENDIENTE',
                    es_cotizacion=True
                )
                print(f"Cotización creada con número {cotizacion.numero_cotizacion}...")

                # Crear los detalles de la cotización
                for item in carrito_items:
                    presentacion = item.presentacion
                    cantidad_paquetes = item.cantidad

                    valor_base, valor_iva = obtener_valor_base_iva(presentacion.precio, porcentaje_iva)
                    subtotal_item = valor_base * cantidad_paquetes
                    iva_item = valor_iva * cantidad_paquetes
                    total_item = subtotal_item + iva_item

                    print(f"Valores de detalle: cantidad={cantidad_paquetes}, precio_unitario={presentacion.precio}, subtotal={subtotal_item}, total={total_item}")

                    detalle = DetalleCotizacion.objects.create(
                        cotizacion=cotizacion,
                        producto=item.producto,
                        presentacion=presentacion,
                        cantidad=cantidad_paquetes * presentacion.cantidad,
                        precio_unitario=presentacion.precio,
                        subtotal=subtotal_item.quantize(Decimal('0.01')),
                        descuento=0,
                        total=total_item.quantize(Decimal('0.01')),
                        valor_iva=iva_item.quantize(Decimal('0.01'))
                    )
                    print(f"Detalle creado: {detalle}")

                if not cotizacion.detalles.exists():
                    print("Error: La cotización no tiene detalles asociados.")
                    raise ValidationError("La cotización no tiene detalles asociados.")

                # **Ajustar inventario después de la creación de la cotización**
                for item in carrito_items:
                    print(f"Ajustando inventario para {item.producto.nombre}...")
                    AjusteInventarioService.ajustar_inventario(item.producto, item.presentacion, item.cantidad)

                print(f"Cotización {cotizacion.numero_cotizacion} completada con {cotizacion.detalles.count()} detalles.")
                return cotizacion

    except Exception as e:
        print(f"Error general en la transacción: {e}")
        raise e


def asignar_pagos_a_cotizacion(cotizacion, metodos_pago, montos_pago):
    metodo_descripciones = {
        '01': 'Efectivo',
        '16': 'Tarjeta de Débito',
        '19': 'Tarjeta de Crédito',
        '20': 'Transferencias',
        '17': 'Dinero Electrónico'
    }

    for metodo_pago, monto_pago in zip(metodos_pago, montos_pago):
        descripcion = metodo_descripciones.get(metodo_pago, 'Método de Pago Desconocido')
        Pago.objects.create(
            cotizacion=cotizacion,  # Cambié factura por cotizacion
            codigo_sri=metodo_pago,
            total=Decimal(monto_pago),
            descripcion=f"Pago con {descripcion}"
        )


def generar_pdf_cotizacion_y_guardar(cotizacion):
    nombre_archivo = f"cotizacion_{cotizacion.numero_cotizacion}.pdf"
    ruta_pdf = os.path.join(settings.MEDIA_ROOT, nombre_archivo)
    generar_pdf_cotizacion(cotizacion, ruta_pdf)  # Debes crear esta función
    return f"/media/{nombre_archivo}"
