from django.shortcuts import render
from .services import generar_reporte_ventas_por_turno
from RegistroTurnos.models import RegistroTurno
from django.contrib.auth.models import User
import pandas as pd
from django.shortcuts import render, get_object_or_404
from .services import generar_reporte_ventas_por_turno
from RegistroTurnos.models import RegistroTurno
from django.http import HttpResponse
from .forms import FiltroReporteVentasForm
from django.db.models import Prefetch
from django_tenants.utils import tenant_context
from django.utils.dateparse import parse_date
from facturacion.models import Factura
from ventas.models import Venta



def reporte_ventas_por_turno(request):
    turno_id = request.GET.get('turno_id')

    # Validar si se ha proporcionado un turno_id
    if not turno_id:
        context = {'error': 'No se ha proporcionado un ID de turno válido.'}
        return render(request, 'reportes/reporte_ventas.html', context)

    # Utilizamos el tenant_context para asegurarnos de que la consulta sea segura
    with tenant_context(request.tenant):
        # Validar que el turno exista
        turno = get_object_or_404(RegistroTurno, id=turno_id)

        # Generar el reporte de ventas asociado a ese turno
        ventas, total_ventas = generar_reporte_ventas_por_turno(turno_id)

    # Preparar el contexto para la plantilla
    context = {
        'ventas': ventas,
        'total_ventas': total_ventas,
        'turno': turno,
    }
    return render(request, 'reportes/reporte_ventas.html', context)



def seleccionar_turno_por_fechas(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    user_id = request.GET.get('user_id')  # Cambiado de empleado_id a user_id

    # Validar que las fechas son válidas
    if not fecha_inicio or not fecha_fin:
        context = {'error': 'Debes proporcionar ambas fechas: inicio y fin.'}
        return render(request, 'reportes/seleccionar_turno.html', context)

    # Asegurar que las fechas estén en formato válido
    fecha_inicio = parse_date(fecha_inicio)
    fecha_fin = parse_date(fecha_fin)
    
    if not fecha_inicio or not fecha_fin:
        context = {'error': 'El formato de las fechas debe ser válido (YYYY-MM-DD).'}
        return render(request, 'reportes/seleccionar_turno.html', context)

    # Verificar que fecha_fin es mayor o igual a fecha_inicio
    if fecha_fin < fecha_inicio:
        context = {'error': 'La fecha final debe ser posterior o igual a la fecha de inicio.'}
        return render(request, 'reportes/seleccionar_turno.html', context)

    # Filtrar turnos por rango de fechas dentro del tenant actual
    with tenant_context(request.tenant):
        turnos = RegistroTurno.objects.filter(inicio_turno__range=[fecha_inicio, fecha_fin])

        # Aplicar filtro por usuario si se seleccionó
        if user_id:
            turnos = turnos.filter(usuario_id=user_id)

        # Si no hay turnos, mostrar un mensaje
        if not turnos.exists():
            context = {'error': 'No se encontraron turnos para las fechas seleccionadas.'}
            return render(request, 'reportes/seleccionar_turno.html', context)

    context = {
        'turnos': turnos,
    }
    return render(request, 'reportes/seleccionar_turno.html', context)



def buscar_turno_por_id(request):
    turno_id = request.GET.get('turno_id')

    # Validar que el turno_id es un número válido
    if turno_id and turno_id.isdigit():
        with tenant_context(request.tenant):
            # Obtener el turno del tenant actual o devolver un 404 si no existe
            turno = get_object_or_404(RegistroTurno, id=turno_id)

            # Generar reporte de ventas
            ventas, total_ventas = generar_reporte_ventas_por_turno(turno_id)

        return render(request, 'reportes/reporte_ventas.html', {'ventas': ventas, 'total_ventas': total_ventas})

    # Si el turno_id no es válido o no se encuentra el turno
    if not turno_id:
        return render(request, 'reportes/buscar_turno.html')

    return render(request, 'reportes/error.html', {'error': 'ID de turno inválido o turno no encontrado.'})


def seleccionar_turno_detallado(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    user_id = request.GET.get('user_id')  # Cambiado de empleado_id a user_id
    sucursal_id = request.GET.get('sucursal_id')

    # Usar el contexto del tenant para filtrar turnos
    with tenant_context(request.tenant):
        # Empezar con una consulta base vacía
        turnos = RegistroTurno.objects.all()

        # Validar y aplicar filtro por rango de fechas
        if fecha_inicio and fecha_fin:
            fecha_inicio = parse_date(fecha_inicio)
            fecha_fin = parse_date(fecha_fin)
            if fecha_inicio and fecha_fin:
                if fecha_fin < fecha_inicio:
                    return render(request, 'reportes/seleccionar_turno_detallado.html', {
                        'error': 'La fecha de fin debe ser mayor o igual a la fecha de inicio.'
                    })
                turnos = turnos.filter(inicio_turno__range=[fecha_inicio, fecha_fin])
            else:
                return render(request, 'reportes/seleccionar_turno_detallado.html', {
                    'error': 'Las fechas proporcionadas no son válidas.'
                })

        # Validar y aplicar filtro por usuario
        if user_id and user_id.isdigit():
            turnos = turnos.filter(usuario_id=user_id)  # Cambiado a usuario_id
        elif user_id:
            return render(request, 'reportes/seleccionar_turno_detallado.html', {
                'error': 'ID de usuario no es válido.'
            })

        # Validar y aplicar filtro por sucursal
        if sucursal_id and sucursal_id.isdigit():
            turnos = turnos.filter(sucursal_id=sucursal_id)
        elif sucursal_id:
            return render(request, 'reportes/seleccionar_turno_detallado.html', {
                'error': 'ID de sucursal no es válido.'
            })

        # Manejar el caso donde no se encuentran turnos
        if not turnos.exists():
            context = {
                'error': 'No se encontraron turnos para los filtros seleccionados.',
                'turnos': None
            }
        else:
            context = {
                'turnos': turnos
            }




def reporte_ventas(request):
    # Usar el contexto del tenant para filtrar las facturas
    with tenant_context(request.tenant):
        # Obtener todas las facturas con sus relaciones necesarias para el reporte
        facturas = Factura.objects.select_related('cliente').prefetch_related(
            Prefetch('ventas', queryset=Venta.objects.select_related('factura')),
            'pagos', 
            'detalles'
        ).all()

        # Calcular los totales para el reporte asegurando que todos los campos sean válidos
        subtotal_acumulado = sum(factura.total_sin_impuestos or 0 for factura in facturas)
        total_iva = sum(factura.valor_iva or 0 for factura in facturas)
        total_a_pagar = sum(factura.total_con_impuestos or 0 for factura in facturas)
        total_descuentos = sum(detalle.descuento or 0 for factura in facturas for detalle in factura.detalles.all())

        # Calcular los totales por método de pago
        total_por_forma_pago = {}
        for factura in facturas:
            for pago in factura.pagos.all():
                if pago.descripcion not in total_por_forma_pago:
                    total_por_forma_pago[pago.descripcion] = 0
                total_por_forma_pago[pago.descripcion] += pago.total or 0

        # Crear una lista de diccionarios para las facturas con la información consolidada
        facturas_data = []
        for factura in facturas:
            facturas_data.append({
                'fecha_emision': factura.fecha_emision if hasattr(factura, 'fecha_emision') else factura.created_at,
                'numero_autorizacion': factura.numero_autorizacion,
                'cliente': factura.cliente.razon_social if factura.cliente else 'Consumidor Final',
                'subtotal': factura.total_sin_impuestos or 0,
                'total_iva': factura.valor_iva or 0,
                'total_con_impuestos': factura.total_con_impuestos or 0,
                'total_descuentos': sum(detalle.descuento or 0 for detalle in factura.detalles.all()),
                'pagos': factura.pagos.all(),
            })

        # Pasar los datos al contexto
        context = {
            'facturas': facturas_data,
            'subtotal_acumulado': subtotal_acumulado,
            'total_iva': total_iva,
            'total_a_pagar': total_a_pagar,
            'total_descuentos': total_descuentos,
            'total_por_forma_pago': total_por_forma_pago,  # Totales por forma de pago
        }

    return render(request, 'reportes/reporte_ventas.html', context)



def reporte_ventas_filtrado(request):
    ventas = Venta.objects.all()  # Inicialmente seleccionar todas las ventas

    # Aplicar filtros según los parámetros enviados en la solicitud
    if request.method == 'GET':
        form = FiltroReporteVentasForm(request.GET)
        if form.is_valid():
            # Asegurar que los filtros se apliquen dentro del contexto del tenant
            with tenant_context(request.tenant):
                if form.cleaned_data['sucursal']:
                    ventas = ventas.filter(sucursal=form.cleaned_data['sucursal'])  # Filtro por sucursal
                if form.cleaned_data['fecha_inicio'] and form.cleaned_data['fecha_fin']:
                    ventas = ventas.filter(fecha__range=[form.cleaned_data['fecha_inicio'], form.cleaned_data['fecha_fin']])  # Filtro por fecha
                if form.cleaned_data['usuario']:
                    ventas = ventas.filter(usuario=form.cleaned_data['usuario'])  # Filtro por usuario
                if form.cleaned_data['turno']:
                    ventas = ventas.filter(turno=form.cleaned_data['turno'])  # Filtro por turno
    else:
        form = FiltroReporteVentasForm()

    # Manejar la exportación a Excel
    if 'exportar_excel' in request.GET:
        # Crear un DataFrame de Pandas con las ventas filtradas
        data = []
        for venta in ventas:
            data.append({
                'Producto': venta.producto.nombre,  # Asegúrate de que 'producto' tiene 'nombre'
                'Cantidad': venta.cantidad,
                'Precio Unitario': venta.precio_unitario,
                'Total Venta': venta.total_venta,
                'Sucursal': venta.sucursal.nombre,  # 'sucursal' tiene relación con 'Sucursal' y contiene 'nombre'
                'Usuario': venta.usuario.username,  # 'usuario' tiene 'username'
                'Turno': venta.turno.id,
                'Fecha': venta.fecha,
            })

        df = pd.DataFrame(data)

        # Crear la respuesta HTTP con el archivo Excel
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="reporte_ventas.xlsx"'
        df.to_excel(response, index=False)
        return response

    # Renderizar el template con los resultados y el formulario de filtros
    return render(request, 'reportes/reporte_ventas_filtrado.html', {'form': form, 'ventas': ventas})


def listar_usuarios(request):
    usuarios = User.objects.all()  # Cambiado a User
    return render(request, 'reportes/seleccionar_turno_fechas.html', {'usuarios': usuarios})
