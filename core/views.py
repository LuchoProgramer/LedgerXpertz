from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Sucursal, Producto, Categoria, Presentacion
from .forms import SucursalForm, ProductoForm, CategoriaForm, PresentacionForm
from django.contrib.auth.decorators import login_required
from django_tenants.utils import tenant_context  # Importante para cambiar el contexto al tenant actual
from django.http import JsonResponse
from django.forms import inlineformset_factory
from empresas.models import Empresa  # Aquí usas el modelo correcto



# Home 
def home(request):
    # Aquí puedes incluir cualquier dato adicional si lo necesitas
    return render(request, 'core/home.html')

# Lista de sucursales
#@login_required
def lista_sucursales(request):
    with tenant_context(request.tenant):
        sucursales = Sucursal.objects.all()  # Esto ahora solo devuelve las sucursales del tenant actual
    return render(request, 'core/lista_sucursales.html', {'sucursales': sucursales})


#@login_required
def crear_sucursal(request):
    with tenant_context(request.tenant):
        print(f"request.tenant en crear_sucursal: {request.tenant}") #Debug en la vista
        if request.method == 'POST':
            form = SucursalForm(request.POST, empresa=request.tenant)
            if form.is_valid():
                sucursal = form.save()
                messages.success(request, f'Sucursal "{sucursal.nombre}" creada exitosamente.')
                return redirect('core:detalle_sucursal', sucursal_id=sucursal.pk)
            else:
                print("Errores del formulario:", form.errors)
                messages.error(request, 'Corrige los errores en el formulario.')
        else:
            form = SucursalForm(empresa=request.tenant)
        return render(request, 'core/crear_editar_sucursal.html', {'form': form, 'sucursal': None, 'empresa':request.tenant})

#@login_required
def editar_sucursal(request, sucursal_id):
    with tenant_context(request.tenant):
        sucursal = get_object_or_404(Sucursal, pk=sucursal_id, empresa=request.tenant)
        if request.method == 'POST':
            form = SucursalForm(request.POST, instance=sucursal, empresa=request.tenant)
            if form.is_valid():
                form.save()
                messages.success(request, 'Sucursal actualizada exitosamente.')
                return redirect('core:detalle_sucursal', sucursal_id=sucursal.pk)
            else:
                print("Errores del formulario:", form.errors)
                messages.error(request, 'Corrige los errores en el formulario.')
        else:
            form = SucursalForm(instance=sucursal, empresa=sucursal.empresa)
        return render(request, 'core/crear_editar_sucursal.html', {'form': form, 'sucursal': sucursal, 'empresa':request.tenant})


def detalle_sucursal(request, sucursal_id):
    sucursal = get_object_or_404(Sucursal, pk=sucursal_id)
    context = {'sucursal': sucursal}
    return render(request, 'core/detalle_sucursal.html', context) #Ruta a tu template.

# Eliminar sucursal
#@login_required
def eliminar_sucursal(request, sucursal_id):
    # Usamos tenant_context para asegurarnos de que la consulta se haga en el esquema del tenant actual
    with tenant_context(request.tenant):
        sucursal = get_object_or_404(Sucursal, id=sucursal_id)

    if request.method == 'POST':
        sucursal.delete()
        messages.success(request, 'Sucursal eliminada exitosamente.')
        return redirect('core:lista_sucursales')  # Redirige a la lista de sucursales

    return render(request, 'core/eliminar_sucursal.html', {'sucursal': sucursal})


def agregar_producto(request):
    tenant = request.tenant  # Obtener el tenant actual
    producto = None

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, empresa=tenant)

        if form.is_valid():
            with tenant_context(tenant):  # Asegurar que el producto se guarde en el esquema correcto
                producto = form.save(commit=False)
                producto.empresa = tenant  # Asociar explícitamente el producto al tenant
                producto.save()

                if hasattr(form, 'save_m2m'):
                    form.save_m2m()

            messages.success(request, 'Producto agregado exitosamente.')
            return redirect('core:lista_productos')
    else:
        form = ProductoForm(empresa=tenant)

    return render(request, 'core/agregar_producto.html', {'form': form})



def lista_productos(request):
    # Verificar si el usuario tiene al menos una sucursal asociada
    if not request.user.sucursales.exists():
        # Redirigir o mostrar un mensaje si no tiene sucursales asociadas
        return redirect('core:sin_sucursal')  # Asumiendo que tienes una vista para este caso

    # Obtener la empresa asociada al usuario (tenant)
    empresa = request.user.sucursales.first().empresa

    # Obtener los productos de la empresa del usuario
    productos = Producto.objects.filter(empresa=empresa)

    # Verificar si el usuario tiene permiso para eliminar productos
    tiene_permiso = request.user.has_perm("core.delete_producto")
    
    # Recopilar la información de las presentaciones relacionadas
    for producto in productos:
        # Buscar la primera presentación asociada al producto y la sucursal correcta
        presentacion = producto.presentaciones.filter(sucursal__empresa=empresa).first()
        if presentacion:
            producto.presentacion_info = presentacion
        else:
            producto.presentacion_info = None
        
        # Asignar la sucursal asociada (si existe)
        producto.sucursal = producto.sucursales.filter(empresa=empresa).first()

    # Contexto con productos y permisos
    context = {
        'productos': productos,
        'tiene_permiso': tiene_permiso,
        'tenant': empresa  # Pasamos la empresa directamente
    }

    return render(request, 'core/lista_productos.html', context)


def sin_sucursal(request):
    return render(request, 'core/sin_sucursal.html')




def productos_por_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    
    # Obtener la empresa (tenant) del usuario
    tenant = request.user.sucursales.first().empresa if request.user.sucursales.exists() else None

    if tenant:
        productos = Producto.objects.filter(categoria=categoria, empresa=tenant)
        
        # Para cada producto, obtener la primera presentación asociada a la empresa (tenant)
        for producto in productos:
            presentacion = producto.presentaciones.filter(sucursal__empresa=tenant).first()
            producto.presentacion_info = presentacion  # Guardamos la presentación asociada en un atributo del producto
    else:
        productos = []

    context = {
        'categoria': categoria,
        'productos': productos,
        'tenant': tenant
    }

    return render(request, 'core/productos_por_categoria.html', context)




def editar_producto(request, producto_id):
    tenant = request.tenant  # Asegurar que tenant está disponible

    with tenant_context(tenant):
        producto = get_object_or_404(Producto, id=producto_id)
        form = ProductoForm(instance=producto)

        if request.method == "POST":
            form = ProductoForm(request.POST, request.FILES, instance=producto)
            if form.is_valid():
                form.save()
                return redirect("core:lista_productos")

    return render(request, "core/editar_producto.html", {
        "form": form,
        "producto": producto,
        "tenant": tenant if tenant.pk else None,  # Evita pasar un tenant vacío
    })



def ver_producto(request, producto_id):
    tenant = request.tenant  # Empresa activa en el contexto del tenant

    with tenant_context(tenant):
        # Buscar el producto dentro del tenant
        producto = get_object_or_404(Producto, id=producto_id, empresa=tenant)

        # Filtrar presentaciones a través de la sucursal, ya que no tienen relación directa con Empresa
        presentaciones = Presentacion.objects.filter(producto=producto, sucursal__empresa=tenant)

    return render(request, 'core/ver_producto.html', {
        'producto': producto,
        'presentaciones': presentaciones,
        'tenant': tenant,  # Pasar el tenant al template si es necesario
    })




def agregar_categoria(request):
    tenant = request.tenant

    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  # Petición AJAX
            if form.is_valid():
                categoria = form.save(commit=False)
                categoria.empresa = tenant
                categoria.save()
                return JsonResponse({
                    'success': True,
                    'categoria_id': categoria.pk,
                    'nombre': categoria.nombre,  # ← IMPORTANTE: Devolver el nombre
                })
            else:
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        
        # Si no es AJAX, redirige a la lista de categorías
        if form.is_valid():
            categoria = form.save(commit=False)
            categoria.empresa = tenant
            categoria.save()
            return redirect('core:lista_categorias')

    else:
        form = CategoriaForm()

    return render(request, 'core/agregar_categoria.html', {'form': form})



def lista_categorias(request):
    tenant = request.tenant  # Obtém o tenant atual da requisição

    with tenant_context(tenant): # Garante que a consulta seja feita no esquema do tenant
        categorias = Categoria.objects.filter(empresa=tenant) # Filtra as categorias pelo tenant atual
        #Ou
        #categorias = Categoria.objects.all()

    return render(request, 'core/lista_categorias.html', {'categorias': categorias, 'tenant': tenant}) # Passa tenant para o template


# Presentaciones

# Crear un formset para Presentacion
PresentacionFormSet = inlineformset_factory(
    Producto,
    Presentacion,
    form=PresentacionForm,  # Ahora usa el ModelForm correcto
    extra=1,
    fields=['nombre_presentacion', 'cantidad', 'precio', 'sucursal']
)



from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django_tenants.utils import tenant_context
from .models import Producto, Presentacion, Sucursal
from .forms import PresentacionFormSet

def agregar_presentaciones_multiples(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id, empresa=request.tenant)
    empresa = request.tenant  # Tenant actual

    if request.method == 'POST':
        formset = PresentacionFormSet(request.POST, instance=producto, form_kwargs={'tenant': empresa})
        
        if formset.is_valid():
            errores = []
            presentaciones_creadas = []

            for form in formset:
                if form.cleaned_data:
                    sucursal = form.cleaned_data.get('sucursal', None)
                    nombre_presentacion = form.cleaned_data.get('nombre_presentacion', "")

                    print(f"⚡ Procesando presentación: {nombre_presentacion} para sucursal: {sucursal}")

                    if not sucursal:
                        errores.append("Error: No se seleccionó una sucursal.")
                        continue

                    if sucursal.empresa != empresa:
                        errores.append(f"La sucursal {sucursal.nombre} no pertenece a la empresa actual.")
                        continue
                    
                    # Verificar si ya existe esta presentación en la misma sucursal
                    if Presentacion.objects.filter(
                        producto=producto,
                        nombre_presentacion=nombre_presentacion,
                        sucursal=sucursal
                    ).exists():
                        errores.append(f'La presentación "{nombre_presentacion}" ya existe en {sucursal.nombre}.')
                        continue
                    
                    # Crear la presentación
                    nueva_presentacion = Presentacion(
                        producto=producto,
                        nombre_presentacion=nombre_presentacion,
                        cantidad=form.cleaned_data['cantidad'],
                        precio=form.cleaned_data['precio'],
                        sucursal=sucursal
                    )
                    nueva_presentacion.save()
                    presentaciones_creadas.append(nueva_presentacion)

            if errores:
                print("❌ Errores encontrados:", errores)
                return JsonResponse({'success': False, 'error': ' | '.join(errores)}, status=400)

            # Enviar JSON con las presentaciones agregadas
            presentaciones_data = [
                {
                    'id': p.id,
                    'nombre_presentacion': p.nombre_presentacion,
                    'cantidad': p.cantidad,
                    'precio': float(p.precio),  # Convertir Decimal a float para JSON
                    'sucursal_nombre': p.sucursal.nombre if p.sucursal else "Sin sucursal"
                }
                for p in presentaciones_creadas
            ]

            print("✅ Presentaciones agregadas correctamente:", presentaciones_data)
            return JsonResponse({'success': True, 'presentaciones': presentaciones_data})

        print("❌ Errores en el FormSet:", formset.errors)
        return JsonResponse({'success': False, 'errors': formset.errors}, status=400)

    else:
        # Obtener las presentaciones existentes del producto y del tenant actual
        presentaciones_existentes = Presentacion.objects.filter(producto=producto, sucursal__empresa=empresa)
        formset = PresentacionFormSet(instance=producto, queryset=presentaciones_existentes, form_kwargs={'tenant': empresa})

        return render(request, 'core/agregar_presentaciones_multiples.html', {
            'formset': formset,
            'producto': producto,
            'presentaciones_existentes': presentaciones_existentes,
        })



def eliminar_presentacion(request, presentacion_id):
    if request.method == 'POST':
        try:
            presentacion = Presentacion.objects.get(id=presentacion_id, producto__empresa=request.tenant)
            presentacion.delete()
            return JsonResponse({'success': True})
        except Presentacion.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Presentación no encontrada o no pertenece a tu empresa.'})
    return JsonResponse({'success': False, 'error': 'Método no permitido.'})


def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id, empresa=request.tenant)

    if request.method == 'POST':
        producto.delete()
        messages.success(request, 'Producto eliminado exitosamente.')
        return redirect('core:lista_productos')

    return render(request, 'core/eliminar_producto.html', {'producto': producto})


