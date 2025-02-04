# ventas/views.py

from django_tenants.utils import tenant_context  # Importar el contexto del tenant
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from RegistroTurnos.models import RegistroTurno
from .forms import SeleccionVentaForm, CierreCajaForm
from .models import Carrito, Venta
from django.utils import timezone
from inventarios.models import Producto
from django.contrib import messages
from django.db.models import Sum
from ventas.models import Venta, CierreCaja
from facturacion.models import Factura, Pago
from decimal import Decimal
from core.models import Sucursal, Presentacion, Categoria
from ventas.services import VentaService
from ventas.services import TurnoService 
from datetime import timedelta
from django.http import JsonResponse, HttpResponseNotAllowed
from django.db import transaction
from .utils import obtener_total_items_en_carrito
from inventarios.models import Inventario
from inventarios.services.validacion_inventario_service import ValidacionInventarioService
from inventarios.services.ajuste_inventario_service import AjusteInventarioService
from inventarios.services.movimiento_inventario_service import MovimientoInventarioService
from inventarios.services.calculo_precio_service import CalculoPrecioService
from inventarios.services.obtener_inventarios_sucursal_service import ObtenerInventariosSucursalService
from django.views.decorators.http import require_POST

@transaction.atomic
def registrar_venta(request):
    print("Verificando turno activo...")
    
    # Usar tenant_context para asegurar que las operaciones se realicen en el tenant correcto
    with tenant_context(request.tenant):
        turno_activo = RegistroTurno.objects.filter(usuario=request.user, fin_turno__isnull=True).first()
        
        if not turno_activo:
            print("Error: No tienes un turno activo.")
            return render(request, 'ventas/error.html', {'mensaje': 'No tienes un turno activo.'})

        if request.method == 'POST':
            form = SeleccionVentaForm(request.POST, sucursal_id=turno_activo.sucursal.id)
            
            if form.is_valid():
                producto = form.cleaned_data['producto']
                presentacion = form.cleaned_data['presentacion']
                cantidad = form.cleaned_data['cantidad']

                print(f"Producto seleccionado: {producto.nombre}, Presentación: {presentacion.nombre_presentacion}, Cantidad seleccionada: {cantidad}")
                print(f"Cada presentación tiene {presentacion.cantidad} unidades.")

                metodo_pago_seleccionado = request.POST.get('metodo_pago')
                metodo_pago = dict(Pago.METODOS_PAGO_SRI).get(metodo_pago_seleccionado)

                if not metodo_pago:
                    form.add_error(None, f"Método de pago no válido: {metodo_pago_seleccionado}")
                    return render(request, 'ventas/registrar_venta.html', {'form': form})

                try:
                    with transaction.atomic():
                        cliente = getattr(turno_activo.usuario, 'cliente', None)
                        if not cliente:
                            form.add_error(None, "No se encontró un cliente asociado al usuario.")
                            return render(request, 'ventas/registrar_venta.html', {'form': form})

                        # 1. Validar inventario
                        if not ValidacionInventarioService.validar_inventario(producto, presentacion, cantidad):
                            return JsonResponse({'error': f'No hay suficiente inventario disponible para {producto.nombre}.'}, status=400)

                        # 2. Calcular el precio usando el servicio
                        total_sin_impuestos = CalculoPrecioService.calcular_precio(presentacion, cantidad)
                        total_con_impuestos = total_sin_impuestos * Decimal('1.12')  # Aplicar impuestos

                        # 3. Crear la factura
                        factura = Factura.objects.create(
                            sucursal=turno_activo.sucursal,
                            cliente=cliente,
                            usuario=turno_activo.usuario,
                            total_sin_impuestos=total_sin_impuestos,
                            total_con_impuestos=total_con_impuestos,
                            estado='AUTORIZADA',
                            registroturno=turno_activo
                        )

                        # 4. Registrar la venta y ajustar el inventario
                        VentaService.registrar_venta(
                            turno_activo=turno_activo, 
                            producto=producto, 
                            cantidad=cantidad,  # Usamos la cantidad directamente
                            factura=factura, 
                            presentacion=presentacion
                        )

                        # 5. Ajustar inventario después de la venta
                        AjusteInventarioService.ajustar_inventario(producto, presentacion, cantidad)

                        return redirect('dashboard')

                except Exception as e:
                    print(f"Error al generar la factura o registrar la venta: {str(e)}")
                    return JsonResponse({'error': f'Error al generar la factura o registrar la venta: {str(e)}'}, status=500)

        else:
            print("Solicitud GET: Mostrando formulario de selección de venta.")
            form = SeleccionVentaForm(sucursal_id=turno_activo.sucursal.id)

        return render(request, 'ventas/registrar_venta.html', {'form': form})



def inicio_turno(request, turno_id):
    # Obtener el turno activo para el usuario dentro del contexto del tenant
    turno = get_object_or_404(RegistroTurno, id=turno_id, usuario=request.user)
    tenant = turno.sucursal.empresa  # Asegurar que estamos usando el tenant correcto

    # Asegurar que las consultas se ejecuten dentro del esquema del tenant
    with tenant_context(tenant):
        print(f"Esquema activo en la vista: {tenant.schema_name}")  # Depuración

        # 🔥 Filtrar categorías y manejar búsqueda
        categoria_seleccionada = request.GET.get('categoria')
        termino_busqueda = request.GET.get('q')
        categorias = Categoria.objects.all()

        # 🔥 Obtener los inventarios de la sucursal del turno activo
        inventarios = ObtenerInventariosSucursalService.obtener_inventarios(turno.sucursal, tenant)

        if categoria_seleccionada:
            inventarios = inventarios.filter(producto__categoria_id=categoria_seleccionada)

        if termino_busqueda:
            inventarios = inventarios.filter(producto__nombre__icontains=termino_busqueda)

        # 🔥 Filtrar presentaciones por la sucursal del turno
        for inventario in inventarios:
            inventario.presentaciones = inventario.producto.presentaciones.filter(sucursal=turno.sucursal)

        # 🔥 Obtener los items del carrito
        carrito_items = Carrito.objects.filter(turno=turno).select_related('producto')

        # 🔥 Validar stock usando el servicio
        for item in carrito_items:
            if not ValidacionInventarioService.validar_stock_disponible(tenant, item.producto, item.cantidad):
                messages.warning(request, f'El producto {item.producto.nombre} ya tiene todo su stock agregado al carrito.')

    # Renderizar la plantilla con los datos necesarios
    return render(request, 'ventas/inicio_turno.html', {
        'turno': turno,
        'inventarios': inventarios,
        'categorias': categorias,
        'carrito_items': carrito_items,
    })





def agregar_al_carrito(request, producto_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)  # Asegurar siempre JSON

    try:
        # Obtener el producto
        producto = get_object_or_404(Producto.objects.select_related('categoria'), id=producto_id)
        print(f"Producto seleccionado: {producto.nombre}")

        # Obtener el turno activo del usuario
        turno = RegistroTurno.objects.filter(usuario=request.user, fin_turno__isnull=True).select_related('sucursal').first()
        if not turno:
            return JsonResponse({'error': 'No tienes un turno activo.'}, status=400)

        tenant = turno.sucursal.empresa  # 🔥 Obtener el tenant correctamente
        print(f"📌 Tenant obtenido: {type(tenant)} | Esquema: {tenant.schema_name}")

        with tenant_context(tenant):
            # Obtener la presentación seleccionada
            presentacion_id = request.POST.get('presentacion')
            if not presentacion_id:
                return JsonResponse({'error': 'Debe seleccionar una presentación.'}, status=400)

            presentacion = get_object_or_404(Presentacion, id=presentacion_id, producto=producto)
            print(f"Presentación seleccionada: {presentacion.nombre_presentacion}")

            # Obtener la cantidad
            cantidad = int(request.POST.get('cantidad', 1))
            total_unidades_solicitadas = presentacion.cantidad * cantidad
            print(f"Total unidades solicitadas: {total_unidades_solicitadas}")

            # 🔥 Corregimos el orden de los argumentos en validar_inventario()
            if not ValidacionInventarioService.validar_inventario(tenant, producto, presentacion, cantidad):
                return JsonResponse({'error': f'No hay suficiente stock para {producto.nombre}.'}, status=400)

            # Obtener o crear el ítem en el carrito
            carrito_item, creado = Carrito.objects.get_or_create(
                turno=turno,
                producto=producto,
                presentacion=presentacion,
                defaults={'cantidad': cantidad}
            )

            if not creado:
                carrito_item.cantidad += cantidad
                carrito_item.save()
                print(f"Carrito actualizado: {carrito_item.producto.nombre} - {carrito_item.cantidad}")

            # Actualizar la sesión
            cart = request.session.get('cart', {})
            key = f"{producto_id}_{presentacion.id}"
            cart[key] = {'producto_id': producto_id, 'presentacion_id': presentacion.id, 'quantity': carrito_item.cantidad}
            request.session['cart'] = cart
            request.session.modified = True
            print("Contenido del carrito en la sesión después de la actualización:", cart)

            return JsonResponse({'message': 'Producto agregado al carrito', 'carrito': cart}, status=200)

    except Exception as e:
        print("Error en agregar_al_carrito:", str(e))
        return JsonResponse({'error': 'Ocurrió un error inesperado', 'details': str(e)}, status=500)



def ver_carrito(request):
    # Obtener el turno activo del usuario con la sucursal ya cargada si se usa en la vista
    turno = RegistroTurno.objects.filter(usuario=request.user, fin_turno__isnull=True).select_related('sucursal').first()
    print(f"Turno activo encontrado: {turno.id} en la sucursal {turno.sucursal.nombre}" if turno else "No hay turno activo.")

    # Verificar si el usuario ha hecho clic en el botón "Eliminar"
    if request.method == 'POST':
        item_id = request.POST.get('item_id')  # Obtener el ID del producto del formulario
        carrito_item = get_object_or_404(Carrito, id=item_id)

        print(f"Eliminando el producto del carrito: {carrito_item.producto.nombre} con presentación {carrito_item.presentacion.nombre_presentacion}")
        
        # Asegurarse de que la eliminación de items se haga dentro del contexto del tenant correcto
        with tenant_context(turno.sucursal.empresa):
            # Eliminar el producto del carrito en la base de datos
            carrito_item.delete()
            
            # Actualizar la sesión para reflejar la eliminación
            cart = request.session.get('cart', {})
            key = f"{carrito_item.producto.id}_{carrito_item.presentacion.id}"
            if key in cart:
                del cart[key]
                request.session['cart'] = cart
                request.session.modified = True
                print("Carrito actualizado en la sesión después de la eliminación:", cart)

        return redirect('ventas:ver_carrito')  # Redirigir al carrito actualizado

    if turno:
        # Asegurarse de que la consulta de los items del carrito se haga en el contexto adecuado
        with tenant_context(turno.sucursal.empresa):
            # Obtener los items del carrito con el producto y presentación precargados
            carrito_items = Carrito.objects.filter(turno=turno).select_related('producto', 'presentacion')
            print(f"Carrito contiene {carrito_items.count()} items.")

            # Actualizar la sesión con los ítems actuales del carrito para mantener sincronización
            cart = {}
            for item in carrito_items:
                key = f"{item.producto.id}_{item.presentacion.id}"
                cart[key] = {
                    'producto_id': item.producto.id,
                    'presentacion_id': item.presentacion.id,
                    'quantity': item.cantidad
                }
            request.session['cart'] = cart
            request.session.modified = True
            print("Carrito sincronizado con la sesión:", cart)

            # Calcular el total utilizando los datos ya cargados
            total = sum(item.subtotal() for item in carrito_items)
            print(f"Total calculado del carrito: {total}")

        return render(request, 'ventas/ver_carrito.html', {
            'carrito_items': carrito_items,
            'total': total,
            'turno': turno
        })
    else:
        print("No hay turno activo.")
        return render(request, 'ventas/error.html', {'mensaje': 'No tienes un turno activo.'})
    

@require_POST
def eliminar_item_carrito(request):
    # Obtener el ID del item a eliminar
    item_id = request.POST.get('item_id')
    
    if item_id:
        try:
            # Obtener el turno activo del usuario
            turno = RegistroTurno.objects.filter(usuario=request.user, fin_turno__isnull=True).first()

            if turno:
                # Usar tenant_context para asegurar que la operación se haga en el contexto correcto
                with tenant_context(turno.sucursal.empresa):
                    # Verificar que el item pertenece al turno activo del usuario
                    carrito_item = get_object_or_404(Carrito, id=item_id, turno=turno)
                    print(f"Eliminando el producto del carrito: {carrito_item.producto.nombre} con presentación {carrito_item.presentacion.nombre_presentacion}")

                    # Eliminar el producto del carrito
                    carrito_item.delete()

                    # Recalcular el total
                    carrito_items = Carrito.objects.filter(turno=turno)
                    total = sum(item.subtotal() for item in carrito_items)
                    
                    # Responder con éxito y el total actualizado
                    return JsonResponse({'success': True, 'total': total})

            else:
                return JsonResponse({'success': False, 'error': 'No tienes un turno activo.'})

        except Carrito.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'El item no existe o no pertenece al usuario.'})
    else:
        return JsonResponse({'success': False, 'error': 'No se proporcionó un ID de item válido.'})
    


@require_POST
def actualizar_cantidad_carrito(request):
    item_id = request.POST.get('item_id')
    nueva_cantidad = request.POST.get('cantidad')
    
    if item_id and nueva_cantidad:
        try:
            nueva_cantidad = int(nueva_cantidad)
            if nueva_cantidad < 1:
                return JsonResponse({'success': False, 'error': 'La cantidad debe ser al menos 1.'})
            
            # Obtener el turno activo del usuario
            turno = RegistroTurno.objects.filter(usuario=request.user, fin_turno__isnull=True).first()
            
            if turno:
                # Usar tenant_context para asegurar que la operación se haga en el contexto correcto
                with tenant_context(turno.sucursal.empresa):
                    # Obtener el item del carrito perteneciente al turno activo
                    carrito_item = get_object_or_404(Carrito, id=item_id, turno=turno)
                    carrito_item.cantidad = nueva_cantidad
                    carrito_item.save()
                    
                    # Calcular el nuevo subtotal y el total del carrito
                    nuevo_subtotal = carrito_item.subtotal()
                    carrito_items = Carrito.objects.filter(turno=turno)
                    total = sum(item.subtotal() for item in carrito_items)
                    
                    # Responder con éxito y los nuevos valores
                    return JsonResponse({
                        'success': True,
                        'nuevo_subtotal': nuevo_subtotal,
                        'total': total
                    })
            else:
                return JsonResponse({'success': False, 'error': 'No tienes un turno activo.'})

        except ValueError:
            return JsonResponse({'success': False, 'error': 'La cantidad debe ser un número entero.'})
        except Carrito.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'El item no existe o no pertenece al usuario.'})
    else:
        return JsonResponse({'success': False, 'error': 'Datos incompletos.'})
    

# ventas/views.py
@login_required
def cerrar_turno(request):
    usuario = request.user
    turno_activo = RegistroTurno.objects.filter(usuario=usuario, fin_turno__isnull=True).first()

    if not turno_activo:
        messages.error(request, "No tienes un turno activo para cerrar.")
        return redirect('ventas:inicio_turno', turno_id=turno_activo.id)

    if request.method == 'POST':
        form = CierreCajaForm(request.POST)
        if form.is_valid():
            try:
                # Usar el servicio para cerrar el turno
                TurnoService.cerrar_turno(turno_activo, form.cleaned_data)
                messages.success(request, "Turno cerrado correctamente.")
                return redirect('dashboard')
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Por favor, revisa los datos ingresados.")
    
    else:
        form = CierreCajaForm()

    return render(request, 'ventas/cierre_caja.html', {'form': form, 'turno': turno_activo})