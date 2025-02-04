from django.shortcuts import render, redirect, get_object_or_404
from django_tenants.utils import tenant_context
from django.core.paginator import Paginator
from .models import Inventario, MovimientoInventario,Transferencia
from core.models import Sucursal, Producto
from django.contrib import messages
from .forms import InventarioForm
from .forms import TransferenciaForm
from .forms import UploadFileForm
from django.http import HttpResponse
import pandas as pd
from django.urls import reverse
from django.http import JsonResponse


def seleccionar_sucursal(request):
    tenant = request.tenant  # Django Tenants obtiene el tenant aquí

    with tenant_context(tenant):  # Asegurar que estamos en el esquema correcto
        sucursales = tenant.sucursales.all()  # Obtener sucursales del tenant

    if request.method == 'POST':
        sucursal_id = request.POST.get('sucursal_id')
        return redirect('inventarios:ver_inventario', sucursal_id=sucursal_id)

    return render(request, 'inventarios/seleccionar_sucursal.html', {'sucursales': sucursales})



def ver_inventario(request, sucursal_id):
    # Obtener la sucursal seleccionada, filtrando por el tenant activo
    sucursal = get_object_or_404(Sucursal, id=sucursal_id, empresa=request.tenant)  # Suponiendo que `empresa` es un ForeignKey a `Empresa`

    # Obtener el inventario para esa sucursal, con el producto relacionado precargado
    inventarios = Inventario.objects.filter(sucursal=sucursal).select_related('producto')

    # Paginación del inventario, 10 elementos por página
    paginator = Paginator(inventarios, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventarios/ver_inventario.html', {
        'sucursal': sucursal,
        'inventarios': page_obj,  # Cambié 'inventario' a 'inventarios' y añadí paginación
    })


def agregar_producto_inventario(request):
    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        sucursal_id = request.POST.get('sucursal_id')
        cantidad = request.POST.get('cantidad')

        # Validar que 'cantidad' no sea nulo ni vacío
        if not cantidad:
            messages.error(request, 'La cantidad es requerida.')
            return redirect('inventarios:agregar_producto_inventario')

        # Intentar convertir 'cantidad' a entero y manejar el error si no es válido
        try:
            cantidad = int(cantidad)
        except ValueError:
            messages.error(request, 'La cantidad debe ser un número válido.')
            return redirect('inventarios:agregar_producto_inventario')

        # Filtrar las sucursales por el tenant actual
        sucursal = get_object_or_404(Sucursal, id=sucursal_id, empresa=request.tenant)

        # Ahora puedes proceder a guardar la cantidad en el inventario
        try:
            inventario, created = Inventario.objects.get_or_create(
                producto_id=producto_id, 
                sucursal=sucursal,  # Usamos el objeto Sucursal en lugar de solo el ID
                defaults={'cantidad': cantidad}
            )
            if not created:
                inventario.cantidad += cantidad  # Sumar cantidad si ya existe el producto
                inventario.save()

            messages.success(request, 'Producto agregado al inventario.')
        except Exception as e:
            messages.error(request, f'Error al agregar el producto: {e}')
        
        return redirect('inventarios:ver_inventario', sucursal_id=sucursal_id)

    else:
        # Aquí puedes cargar cualquier dato necesario para el formulario
        productos = Producto.objects.all()
        sucursales = Sucursal.objects.filter(empresa=request.tenant)  # Filtramos las sucursales por el tenant actual
        return render(request, 'inventarios/agregar_producto.html', {'productos': productos, 'sucursales': sucursales})


def ajustar_inventario(request, producto_id, sucursal_id):
    # Asegúrate de que la sucursal esté asociada al tenant correcto
    sucursal = get_object_or_404(Sucursal, id=sucursal_id, empresa=request.tenant)
    producto = get_object_or_404(Producto, id=producto_id)

    # Asegúrate de que el inventario esté asociado a la sucursal y al tenant
    inventario = get_object_or_404(Inventario, producto=producto, sucursal=sucursal)

    if request.method == 'POST':
        nueva_cantidad = request.POST.get('nueva_cantidad')

        # Validar que la nueva cantidad es un número entero válido
        try:
            nueva_cantidad = int(nueva_cantidad)
            if nueva_cantidad < 0:
                raise ValueError("La cantidad no puede ser negativa")
        except ValueError:
            # Si la cantidad no es válida, podrías mostrar un mensaje de error
            return render(request, 'inventarios/ajustar_inventario.html', {
                'inventario': inventario,
                'producto': producto,
                'sucursal': sucursal,
                'error': 'La cantidad debe ser un número entero válido y no negativo.'
            })

        # Actualizamos la cantidad en el inventario
        inventario.cantidad = nueva_cantidad
        inventario.save()

        # Redirigir al inventario de la sucursal, pasando el sucursal_id correctamente
        messages.success(request, 'Inventario ajustado correctamente.')
        return redirect('inventarios:ver_inventario', sucursal_id=sucursal.id)

    return render(request, 'inventarios/ajustar_inventario.html', {
        'inventario': inventario,
        'producto': producto,
        'sucursal': sucursal
    })




def crear_transferencia(request):
    tenant = request.tenant  # Obtener el tenant actual

    with tenant_context(tenant):  # Asegurar que las consultas se hagan dentro del esquema correcto
        if request.method == 'POST':
            form = TransferenciaForm(request.POST, tenant=tenant)  # 🔹 Se pasa `tenant`
            if form.is_valid():
                transferencia = form.save(commit=False)

                # Filtrar sucursales por tenant
                sucursal_origen = get_object_or_404(Sucursal, id=transferencia.sucursal_origen.id, empresa=tenant)
                sucursal_destino = get_object_or_404(Sucursal, id=transferencia.sucursal_destino.id, empresa=tenant)

                # Buscar inventario en la sucursal de origen
                inventario_origen = Inventario.objects.filter(sucursal=sucursal_origen, producto=transferencia.producto).first()

                if not inventario_origen:
                    form.add_error('producto', 'El producto seleccionado no está disponible en la sucursal de origen.')
                elif inventario_origen.cantidad < transferencia.cantidad:
                    form.add_error('cantidad', f'No hay suficiente stock en la sucursal de origen ({inventario_origen.cantidad} disponibles).')
                else:
                    # Descontar productos de la sucursal de origen
                    inventario_origen.cantidad -= transferencia.cantidad
                    inventario_origen.save()

                    # Agregar productos a la sucursal destino
                    inventario_destino, created = Inventario.objects.get_or_create(
                        sucursal=sucursal_destino,
                        producto=transferencia.producto,
                        defaults={'cantidad': 0}  # Si no existe, inicia en 0
                    )

                    inventario_destino.cantidad += transferencia.cantidad
                    inventario_destino.save()

                    # Guardar la transferencia
                    transferencia.save()

                    # Registrar movimientos de inventario
                    MovimientoInventario.objects.create(
                        sucursal=sucursal_origen,
                        producto=transferencia.producto,
                        cantidad_transferida=transferencia.cantidad,
                        tipo_movimiento='Salida por Transferencia',
                        fecha=transferencia.fecha,
                    )
                    MovimientoInventario.objects.create(
                        sucursal=sucursal_destino,
                        producto=transferencia.producto,
                        cantidad_transferida=transferencia.cantidad,
                        tipo_movimiento='Entrada por Transferencia',
                        fecha=transferencia.fecha,
                    )

                    messages.success(request, f'Transferencia realizada correctamente. {transferencia.cantidad} unidades movidas.')
                    return redirect('inventarios:lista_transferencias')

        else:
            form = TransferenciaForm(tenant=tenant)  # 🔹 Se pasa `tenant` para filtrar datos correctamente

    return render(request, 'inventarios/crear_transferencia.html', {
        'form': form
    })


def lista_transferencias(request):
    transferencias = Transferencia.objects.filter(sucursal_origen__empresa=request.tenant, sucursal_destino__empresa=request.tenant)
    return render(request, 'inventarios/lista_transferencias.html', {'transferencias': transferencias})

def lista_movimientos_inventario(request):
    movimientos = MovimientoInventario.objects.filter(sucursal__empresa=request.tenant).order_by('-fecha')
    return render(request, 'inventarios/lista_movimientos_inventario.html', {'movimientos': movimientos})



def agregar_inventario_manual(request, sucursal_id):
    tenant = request.tenant  # Obtener el tenant actual

    with tenant_context(tenant):  # Asegurar que la consulta se haga dentro del esquema correcto
        sucursal = get_object_or_404(Sucursal, id=sucursal_id, empresa=tenant)  # Filtrar por el tenant actual

        if request.method == 'POST':
            form = InventarioForm(request.POST, tenant=tenant)  # 🔹 Ahora pasamos tenant correctamente
            if form.is_valid():
                inventario, created = Inventario.objects.get_or_create(
                    producto=form.cleaned_data['producto'],
                    sucursal=sucursal,
                    defaults={'cantidad': form.cleaned_data['cantidad']}
                )
                if not created:
                    inventario.cantidad += form.cleaned_data['cantidad']
                inventario.save()

                return redirect('inventarios:ver_inventario', sucursal_id=sucursal.id)
        else:
            form = InventarioForm(tenant=tenant)  # 🔹 Pasa tenant al formulario

    return render(request, 'inventarios/agregar_inventario_manual.html', {
        'form': form, 
        'sucursal': sucursal
    })



def cargar_inventario_excel(request, sucursal_id):
    """Vista para cargar inventario desde un archivo Excel en un esquema multitenant."""

    # Obtener el tenant actual
    tenant = request.tenant

    with tenant_context(tenant):  # Asegurar que las consultas se hagan dentro del esquema correcto
        sucursal = get_object_or_404(Sucursal, id=sucursal_id, empresa=tenant)  # Filtrar por empresa

        if request.method == 'POST':
            form = UploadFileForm(request.POST, request.FILES)

            if form.is_valid():
                file = request.FILES['file']
                df = pd.read_excel(file)

                # Verificar que el archivo tiene las columnas necesarias
                required_columns = ['Nombre', 'Cantidad']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    return HttpResponse(f"El archivo debe contener las siguientes columnas: {', '.join(missing_columns)}")

                # Iterar por las filas del DataFrame y actualizar el inventario
                errores = []  # Para almacenar errores si hay productos inexistentes
                for index, row in df.iterrows():
                    try:
                        producto = Producto.objects.get(nombre=row['Nombre'], empresa=tenant)  # Filtrar por tenant
                        inventario, created = Inventario.objects.get_or_create(
                            producto=producto,
                            sucursal=sucursal,
                            defaults={'cantidad': row['Cantidad']}
                        )

                        # Si el inventario ya existe, actualizar la cantidad
                        if not created:
                            inventario.cantidad = row['Cantidad']
                            inventario.save()

                    except Producto.DoesNotExist:
                        errores.append(f"El producto '{row['Nombre']}' no existe en esta empresa.")

                # Si hubo errores, mostrarlos
                if errores:
                    return HttpResponse("<br>".join(errores))

                return redirect(reverse('inventarios:ver_inventario', args=[sucursal.id]))

        else:
            form = UploadFileForm()

    return render(request, 'inventarios/cargar_inventario_excel.html', {'form': form, 'sucursal': sucursal})



def obtener_stock_disponible(request, sucursal_id, producto_id):
    """API para obtener el stock disponible en una sucursal"""
    tenant = request.tenant  # Obtener el tenant actual

    with tenant_context(tenant):
        inventario = Inventario.objects.filter(sucursal_id=sucursal_id, producto_id=producto_id).first()
        stock = inventario.cantidad if inventario else 0  # Si no hay inventario, devolver 0

    return JsonResponse({'stock': stock})