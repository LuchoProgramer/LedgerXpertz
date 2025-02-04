from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ConteoProductoForm
from .models import ConteoDiario
from core.models import Producto, Categoria
from .utils import generar_y_enviar_excel
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from RegistroTurnos.models import RegistroTurno
from django.utils.timezone import now
from django_tenants.utils import tenant_context  # Importa tenant_context
from inventarios.models import Inventario

@login_required
def registrar_conteo(request):
    with tenant_context(request.tenant):  # Asegura que todo esté en el contexto del tenant actual
        # Obtener el turno activo del usuario
        turno_activo = RegistroTurno.objects.filter(usuario=request.user, fin_turno__isnull=True).first()
        
        if not turno_activo:
            # Si no hay turno activo, redirigir al dashboard
            return redirect('dashboard')

        # Obtener la sucursal activa desde el turno
        sucursal_activa = turno_activo.sucursal

        # Obtener los productos de la sucursal activa
        inventarios = Inventario.objects.filter(sucursal=sucursal_activa)
        productos = [inventario.producto for inventario in inventarios]

        # Filtrar por categoría si está seleccionada
        categoria_seleccionada = None
        if request.method == 'POST':
            form = ConteoProductoForm(request.POST, productos=productos)
            if form.is_valid():
                # Guardar los registros de conteo para cada producto
                for producto in productos:
                    cantidad = form.cleaned_data.get(f'cantidad_{producto.id}', None)
                    if cantidad is not None:
                        ConteoDiario.objects.create(
                            sucursal=sucursal_activa,
                            usuario=request.user,
                            fecha_conteo=now().date(),
                            producto=producto,
                            cantidad_contada=cantidad
                        )

                # Generar y enviar el archivo Excel
                email_destino = 'luchoviteri1990@gmail.com'  # Cambiar a email adecuado
                try:
                    generar_y_enviar_excel(sucursal_activa, request.user, email_destino)
                    messages.success(request, "El conteo se ha registrado y enviado correctamente.")
                except Exception as e:
                    messages.error(request, f"El conteo se registró, pero no se pudo enviar el correo: {str(e)}")

                # Redirigir a la página de conteo exitoso
                return redirect('conteo_exitoso')
        else:
            categoria_seleccionada = request.GET.get('categoria')
            if categoria_seleccionada:
                # Filtrar productos por categoría seleccionada
                productos = [producto for producto in productos if str(producto.categoria.id) == categoria_seleccionada]
        
            form = ConteoProductoForm(productos=productos)
            form.fields['categoria'].initial = categoria_seleccionada

        context = {
            'form': form,
            'categorias': Categoria.objects.all(),
            'categoria_seleccionada': categoria_seleccionada,
            'turno': turno_activo,
            'sucursal_activa': sucursal_activa,
        }

        return render(request, 'conteo/registrar_conteo.html', context)
    

def conteo_exitoso(request):
    return render(request, 'conteo/conteo_exitoso.html')
