from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from decimal import Decimal
from django_tenants.utils import tenant_context

# Constantes de márgenes
MARGEN_X = 50
MARGEN_Y = 50

def obtener_valor_base_iva(precio_con_iva, porcentaje_iva):
    porcentaje_iva_decimal = Decimal(porcentaje_iva) / Decimal('100')
    valor_base = precio_con_iva / (1 + porcentaje_iva_decimal)
    valor_iva = precio_con_iva - valor_base
    return valor_base, valor_iva

def configurar_documento(nombre_archivo):
    c = canvas.Canvas(nombre_archivo, pagesize=A4)
    c.setTitle("Factura")
    return c

def agregar_cabecera(c, factura):
    print(f"Generando cabecera para la factura: {factura.numero_autorizacion}")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGEN_X, 800, f"Nombre Comercial: {factura.sucursal.nombre}")
    c.setFont("Helvetica", 10)
    c.drawString(MARGEN_X, 780, f"Razón Social: {factura.sucursal.razon_social.nombre}")
    c.drawString(MARGEN_X, 760, f"RUC: {factura.sucursal.razon_social.ruc}")
    c.drawString(MARGEN_X, 740, f"Dirección: {factura.sucursal.direccion}")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGEN_X, 720, f"Factura: {factura.numero_autorizacion}")
    c.setFont("Helvetica", 10)
    c.drawString(MARGEN_X, 700, f"Fecha de Emisión: {factura.fecha_emision.strftime('%d/%m/%Y')}")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGEN_X, 680, f"Cliente: {factura.cliente.razon_social}")
    c.setFont("Helvetica", 10)
    c.drawString(MARGEN_X, 660, f"Tipo Identificación: {factura.cliente.tipo_identificacion}")
    c.drawString(MARGEN_X, 640, f"Identificación: {factura.cliente.identificacion}")
    c.drawString(MARGEN_X, 620, f"Dirección Cliente: {factura.cliente.direccion if factura.cliente.direccion else 'N/A'}")
    return c

def agregar_detalles_productos(c, factura):
    y = 580
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGEN_X, y, "Detalles de los productos/servicios:")
    y -= 20
    c.setFont("Helvetica", 10)

    for detalle in factura.detalles.all():
        presentacion_nombre = detalle.presentacion.nombre_presentacion
        precio_con_iva = Decimal(detalle.precio_unitario)
        cantidad_presentaciones = detalle.cantidad // detalle.presentacion.cantidad
        porcentaje_iva = Decimal('15')

        # Desglosar el valor base e IVA para la presentación
        valor_base, valor_iva = obtener_valor_base_iva(precio_con_iva, porcentaje_iva)
        subtotal = valor_base * cantidad_presentaciones
        total_iva = valor_iva * cantidad_presentaciones
        total = subtotal + total_iva

        # Formatear la línea de detalle en el PDF
        c.drawString(
            MARGEN_X, y,
            f"{detalle.producto.nombre} - {presentacion_nombre} - {cantidad_presentaciones} x {precio_con_iva:.2f} = {total:.2f}"
        )
        print(f"Producto: {detalle.producto.nombre}, Presentación: {presentacion_nombre}, "
              f"Presentaciones: {cantidad_presentaciones}, Precio con IVA: {precio_con_iva:.2f}, Subtotal: {subtotal:.2f}, IVA: {total_iva:.2f}, Total: {total:.2f}")

        y -= 20

        # Verificar si se necesita un salto de página
        if y < 100:
            c.showPage()
            agregar_cabecera(c, factura)
            y = 800
            c.setFont("Helvetica", 10)

    return c

def agregar_totales(c, factura):
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGEN_X, 200, "Totales:")
    c.setFont("Helvetica", 10)

    total_sin_impuestos = Decimal('0.00')
    total_iva = Decimal('0.00')
    total_con_impuestos = Decimal('0.00')
    porcentaje_iva = Decimal('15')

    # Iterar sobre los detalles para sumar correctamente los totales
    for detalle in factura.detalles.all():
        precio_con_iva = Decimal(detalle.precio_unitario)
        cantidad_presentaciones = detalle.cantidad // detalle.presentacion.cantidad

        # Desglosar el valor base e IVA para la presentación
        valor_base, valor_iva = obtener_valor_base_iva(precio_con_iva, porcentaje_iva)
        subtotal = valor_base * cantidad_presentaciones
        total_iva_item = valor_iva * cantidad_presentaciones
        total_item = subtotal + total_iva_item

        total_sin_impuestos += subtotal
        total_iva += total_iva_item
        total_con_impuestos += total_item

    c.drawString(MARGEN_X, 180, f"Subtotal sin impuestos: {total_sin_impuestos:.2f}")
    c.drawString(MARGEN_X, 160, f"Impuestos (IVA {porcentaje_iva}%): {total_iva:.2f}")
    c.drawString(MARGEN_X, 140, f"Total con impuestos: {total_con_impuestos:.2f}")

    print(f"Subtotal calculado: {total_sin_impuestos}, Total con IVA: {total_con_impuestos}, IVA: {total_iva}")

    return c

def agregar_mensaje_legal(c):
    c.setFont("Helvetica", 8)
    c.drawString(MARGEN_X, 120, "Este documento no tiene derecho a crédito tributario.")
    return c

def generar_pdf_factura(factura, nombre_archivo):
    tenant = factura.sucursal.empresa  # Obtener el tenant correspondiente
    with tenant_context(tenant):
        c = configurar_documento(nombre_archivo)
        c = agregar_cabecera(c, factura)
        c = agregar_detalles_productos(c, factura)
        c = agregar_totales(c, factura)
        c = agregar_mensaje_legal(c)
        c.showPage()
        c.save()