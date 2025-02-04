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
    c.setTitle("Cotización")
    return c

def agregar_cabecera(c, cotizacion):
    print(f"Generando cabecera para la cotización: {cotizacion.numero_cotizacion}")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGEN_X, 800, f"Nombre Comercial: {cotizacion.sucursal.nombre}")
    c.setFont("Helvetica", 10)
    c.drawString(MARGEN_X, 780, f"Razón Social: {cotizacion.sucursal.razon_social.nombre}")
    c.drawString(MARGEN_X, 760, f"RUC: {cotizacion.sucursal.razon_social.ruc}")
    c.drawString(MARGEN_X, 740, f"Dirección: {cotizacion.sucursal.direccion}")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGEN_X, 720, f"Cotización: {cotizacion.numero_cotizacion}")
    c.setFont("Helvetica", 10)
    c.drawString(MARGEN_X, 700, f"Fecha de Emisión: {cotizacion.fecha_emision.strftime('%d/%m/%Y')}")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGEN_X, 680, f"Cliente: {cotizacion.cliente.razon_social}")
    c.setFont("Helvetica", 10)
    c.drawString(MARGEN_X, 660, f"Tipo Identificación: {cotizacion.cliente.tipo_identificacion}")
    c.drawString(MARGEN_X, 640, f"Identificación: {cotizacion.cliente.identificacion}")
    c.drawString(MARGEN_X, 620, f"Dirección Cliente: {cotizacion.cliente.direccion if cotizacion.cliente.direccion else 'N/A'}")
    return c

def agregar_detalles_productos(c, cotizacion):
    y = 580
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGEN_X, y, "Detalles de los productos/servicios:")
    y -= 20
    c.setFont("Helvetica", 10)

    for detalle in cotizacion.detalles.all():
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
            agregar_cabecera(c, cotizacion)
            y = 800
            c.setFont("Helvetica", 10)

    return c

def agregar_totales(c, cotizacion):
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGEN_X, 200, "Totales:")
    c.setFont("Helvetica", 10)

    total_sin_impuestos = Decimal('0.00')
    total_iva = Decimal('0.00')
    total_con_impuestos = Decimal('0.00')
    porcentaje_iva = Decimal('15')

    # Iterar sobre los detalles para sumar correctamente los totales
    for detalle in cotizacion.detalles.all():
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

def generar_pdf_cotizacion(cotizacion, nombre_archivo):
    """
    Genera un PDF de cotización y lo guarda en la ruta especificada.
    """
    tenant = cotizacion.sucursal.empresa  # Obtener el tenant correspondiente
    with tenant_context(tenant):
        c = configurar_documento(nombre_archivo)
        c = agregar_cabecera(c, cotizacion)
        c = agregar_detalles_productos(c, cotizacion)
        c = agregar_totales(c, cotizacion)
        c = agregar_mensaje_legal(c)
        c.showPage()
        c.save()