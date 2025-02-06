from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django_tenants.utils import tenant_context
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from decimal import Decimal
from facturacion.services import crear_factura, asignar_pagos_a_factura, obtener_o_crear_cliente
from inventarios.services.validacion_inventario_service import ValidacionInventarioService
from RegistroTurnos.models import RegistroTurno
from facturacion.models import Impuesto, Cliente
from facturacion.forms import ImpuestoForm
from ventas.models import Carrito
from ventas.utils import obtener_carrito
from .services import generar_pdf_factura_y_guardar
from .models import Cliente
from facturacion.services import crear_cotizacion, asignar_pagos_a_cotizacion, generar_pdf_cotizacion_y_guardar
from django.http import FileResponse
import os
from django.conf import settings
from .models import Cotizacion
from .pdf.generar_pdf_cotizacion import generar_pdf_cotizacion
from django.views.decorators.http import require_POST
from facturacion.forms import ClienteForm



@transaction.atomic
def generar_factura(request):
    tenant = request.tenant  # Obtener el tenant actual
    if request.method == 'POST':
        print(f"POST request para generar factura en tenant {tenant.schema_name}")

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            try:
                # Obtener los datos del formulario
                cliente_id = request.POST.get('cliente_id')
                identificacion = request.POST.get('identificacion')

                if not cliente_id and not identificacion:
                    return JsonResponse({'error': 'Debes seleccionar un cliente o ingresar los datos de un nuevo cliente.'}, status=400)

                # Filtrar clientes dentro del tenant usando dirección que contiene el nombre de la sucursal
                data_cliente = {
                    'tipo_identificacion': request.POST.get('tipo_identificacion'),
                    'razon_social': request.POST.get('razon_social'),
                    'direccion': request.POST.get('direccion'),
                    'telefono': request.POST.get('telefono'),
                    'email': request.POST.get('email')
                }

                usuario = request.user
                turno_activo = RegistroTurno.objects.filter(
                    usuario=usuario, fin_turno__isnull=True
                ).select_related('sucursal').first()

                if not turno_activo:
                    return JsonResponse({'error': 'No tienes un turno activo.'}, status=400)

                sucursal = turno_activo.sucursal

                # Filtrar clientes basados en la dirección de la sucursal
                clientes = Cliente.objects.filter(direccion__icontains=sucursal.nombre)

                # Si `cliente_id` fue enviado, intentamos encontrar el cliente en la base de datos
                if cliente_id:
                    cliente = Cliente.objects.filter(id=cliente_id, direccion__icontains=sucursal.nombre).first()
                else:
                    # Si no existe, creamos uno nuevo con los datos ingresados
                    cliente = Cliente.objects.create(**data_cliente)

                # Obtener carrito dentro del tenant
                carrito_items = Carrito.objects.filter(turno=turno_activo).select_related('producto', 'presentacion')

                if not carrito_items.exists():
                    return JsonResponse({'error': 'El carrito está vacío. No se puede generar una factura.'}, status=400)

                # Verificar inventario
                for item in carrito_items:
                    if not ValidacionInventarioService.validar_inventario(item.producto, item.presentacion, item.cantidad):
                        return JsonResponse({'error': f'No hay suficiente inventario para {item.producto.nombre}.'}, status=400)

                # Crear factura dentro del tenant
                factura = crear_factura(cliente, sucursal, usuario, carrito_items, tenant)

                # Procesar pagos
                metodos_pago = request.POST.getlist('metodos_pago[]')
                montos_pago = [Decimal(monto) for monto in request.POST.getlist('montos_pago[]')]

                if sum(montos_pago) != factura.total_con_impuestos:
                    return JsonResponse({'error': 'El total pagado no coincide con el total de la factura.'}, status=400)

                asignar_pagos_a_factura(factura, metodos_pago, montos_pago)

                # Generar PDF en el contexto del tenant
                with tenant_context(tenant):
                    pdf_url = generar_pdf_factura_y_guardar(factura)

                carrito_items.delete()

                return JsonResponse({'success': True, 'pdf_url': pdf_url, 'redirect_url': reverse('ventas:inicio_turno', args=[turno_activo.id])})

            except Exception as e:
                return JsonResponse({'error': f'Ocurrió un error: {str(e)}'}, status=500)

    else:
        # Manejo de GET: Filtrar clientes por sucursal usando dirección
        turno_activo = RegistroTurno.objects.filter(
            usuario=request.user, fin_turno__isnull=True
        ).select_related('sucursal').first()

        if not turno_activo:
            return render(request, 'facturacion/error.html', {'mensaje': 'No tienes un turno activo.'})

        sucursal = turno_activo.sucursal
        clientes = Cliente.objects.filter(direccion__icontains=sucursal.nombre)  # Filtrar clientes por sucursal

        carrito_items = Carrito.objects.filter(turno=turno_activo).select_related('producto')
        total_factura = sum(item.subtotal() for item in carrito_items)

        return render(request, 'facturacion/generar_factura.html', {
            'clientes': clientes,
            'total_factura': total_factura,
        })




def crear_impuesto(request):
    with tenant_context(request.tenant):
        if request.method == 'POST':
            form = ImpuestoForm(request.POST)
            if form.is_valid():
                impuesto = form.save(commit=False)  # No guardamos aún
                impuesto.empresa = request.tenant  # Asignamos la empresa del tenant
                impuesto.save()
                messages.success(request, 'Impuesto creado correctamente.')
                return redirect('facturacion:lista_impuestos')
            else:
                messages.error(request, 'Corrige los errores en el formulario.')
        else:
            form = ImpuestoForm()
    return render(request, 'facturacion/crear_impuesto.html', {'form': form})




def lista_impuestos(request):
    # Usar tenant_context para asegurar que la consulta se ejecute dentro del contexto del tenant adecuado
    with tenant_context(request.tenant):
        # No necesitamos obtener la empresa manualmente porque el tenant ya nos da el contexto correcto
        impuestos = Impuesto.objects.all()  # Traemos todos los impuestos del tenant actual

    return render(request, 'facturacion/lista_impuestos.html', {'impuestos': impuestos})



from facturacion.services import crear_cotizacion, asignar_pagos_a_cotizacion, generar_pdf_cotizacion_y_guardar


@transaction.atomic
def generar_cotizacion(request):
    tenant = request.tenant  # Obtener el tenant actual
    if request.method == 'POST':
        print(f"POST request para generar cotización en tenant {tenant.schema_name}")

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            try:
                # Obtener los datos del formulario
                cliente_id = request.POST.get('cliente_id')
                identificacion = request.POST.get('identificacion')

                if not cliente_id and not identificacion:
                    return JsonResponse({'error': 'Debes seleccionar un cliente o ingresar los datos de un nuevo cliente.'}, status=400)

                # Filtrar clientes dentro del tenant
                data_cliente = {
                    'tipo_identificacion': request.POST.get('tipo_identificacion'),
                    'razon_social': request.POST.get('razon_social'),
                    'direccion': request.POST.get('direccion'),
                    'telefono': request.POST.get('telefono'),
                    'email': request.POST.get('email')
                }
                cliente = obtener_o_crear_cliente(cliente_id, identificacion, data_cliente, tenant)

                usuario = request.user
                turno_activo = RegistroTurno.objects.filter(
                    usuario=usuario, fin_turno__isnull=True, sucursal__empresa=tenant
                ).select_related('sucursal').first()

                if not turno_activo:
                    return JsonResponse({'error': 'No tienes un turno activo.'}, status=400)

                sucursal = turno_activo.sucursal

                # Obtener carrito dentro del tenant
                carrito_items = Carrito.objects.filter(turno=turno_activo).select_related('producto', 'presentacion')

                if not carrito_items.exists():
                    return JsonResponse({'error': 'El carrito está vacío. No se puede generar una cotización.'}, status=400)

                # Verificar inventario
                for item in carrito_items:
                    if not ValidacionInventarioService.validar_inventario(item.producto, item.presentacion, item.cantidad, tenant):
                        return JsonResponse({'error': f'No hay suficiente inventario para {item.producto.nombre}.'}, status=400)

                # Crear cotización dentro del tenant
                cotizacion = crear_cotizacion(cliente, sucursal, usuario, carrito_items, tenant)

                # Procesar pagos (en cotización solo se guarda la referencia de pagos, no se cobran)
                metodos_pago = request.POST.getlist('metodos_pago[]')
                montos_pago = [Decimal(monto) for monto in request.POST.getlist('montos_pago[]')]

                if sum(montos_pago) != cotizacion.total_con_impuestos:
                    return JsonResponse({'error': 'El total ingresado no coincide con el total de la cotización.'}, status=400)

                asignar_pagos_a_cotizacion(cotizacion, metodos_pago, montos_pago)

                # Generar PDF en el contexto del tenant
                with tenant_context(tenant):
                    pdf_url = generar_pdf_cotizacion_y_guardar(cotizacion)

                return JsonResponse({'success': True, 'pdf_url': pdf_url, 'redirect_url': reverse('ventas:inicio_turno', args=[turno_activo.id])})

            except Exception as e:
                return JsonResponse({'error': f'Ocurrió un error: {str(e)}'}, status=500)

    else:
        # Manejo de GET
        clientes = Cliente.objects.filter(empresa=tenant)  # Filtrar clientes por tenant
        carrito_items = obtener_carrito(request.user).select_related('producto')
        total_cotizacion = sum(item.subtotal() for item in carrito_items)

        return render(request, 'facturacion/generar_cotizacion.html', {
            'clientes': clientes,
            'total_cotizacion': total_cotizacion,
        })



def generar_pdf_cotizacion_view(request, cotizacion_id):
    """
    Genera el PDF de una cotización y lo devuelve como respuesta.
    """
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)

    # Ruta donde se guardará el PDF
    nombre_archivo = f"cotizacion_{cotizacion.numero_cotizacion}.pdf"
    ruta_pdf = os.path.join(settings.MEDIA_ROOT, nombre_archivo)

    # Generar el PDF si no existe
    if not os.path.exists(ruta_pdf):
        generar_pdf_cotizacion(cotizacion, ruta_pdf)

    # Devolver el PDF como respuesta
    return FileResponse(open(ruta_pdf, "rb"), content_type="application/pdf", as_attachment=True, filename=nombre_archivo)





@require_POST
def crear_cliente_ajax(request):
    tenant = request.tenant

    with tenant_context(tenant):
        data = request.POST

        # Validación antes de intentar crear un cliente
        if Cliente.objects.filter(identificacion=data.get('identificacion')).exists():
            return JsonResponse({'success': False, 'errors': {'identificacion': ['Ya existe un cliente con esta identificación.']}}, status=400)

        if Cliente.objects.filter(email=data.get('email')).exists():
            return JsonResponse({'success': False, 'errors': {'email': ['El correo electrónico ya está en uso.']}}, status=400)

        form = ClienteForm(data)
        if form.is_valid():
            cliente = form.save()
            return JsonResponse({'success': True, 'cliente_id': cliente.id, 'razon_social': cliente.razon_social, 'identificacion': cliente.identificacion})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
