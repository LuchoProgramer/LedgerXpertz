from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .forms import ProveedorForm, DetalleCompraForm, CompraForm
from .models import Proveedor, Compra, DetalleCompra
from django_tenants.utils import tenant_context
from django.forms import inlineformset_factory
from decimal import Decimal, ROUND_HALF_UP, getcontext
from django.core.exceptions import ValidationError
from facturacion.models import Impuesto
import xml.etree.ElementTree as ET
from django.utils import timezone
from .forms import CompraXMLForm
from core.models import Producto, Sucursal

def crear_proveedor(request):
    with tenant_context(request.tenant):  # Asegura que el proveedor se asocia al tenant actual
        if request.method == 'POST':
            form = ProveedorForm(request.POST)
            if form.is_valid():
                proveedor = form.save(commit=False)
                proveedor.empresa = request.tenant  # Asociar al tenant actual (empresa)
                proveedor.save()
                messages.success(request, f'Proveedor "{proveedor.nombre}" creado exitosamente.')
                return redirect('proveedores:detalle', proveedor_id=proveedor.pk)
            else:
                messages.error(request, 'Corrige los errores en el formulario.')
        else:
            form = ProveedorForm()

        return render(request, 'proveedores/crear_editar_proveedor.html', {'form': form})



def editar_proveedor(request, proveedor_id):
    with tenant_context(request.tenant):
        proveedor = get_object_or_404(Proveedor, id=proveedor_id, empresa=request.tenant)
        if request.method == 'POST':
            form = ProveedorForm(request.POST, instance=proveedor)
            if form.is_valid():
                form.save()
                messages.success(request, f'Proveedor "{proveedor.nombre}" actualizado exitosamente.')
                return redirect('proveedores:detalle', proveedor_id=proveedor.pk)
            else:
                print("Errores del formulario:", form.errors)
                messages.error(request, 'Corrige los errores en el formulario.')
        else:
            form = ProveedorForm(instance=proveedor)

        return render(request, 'proveedores/crear_editar_proveedor.html', {'form': form, 'proveedor': proveedor})


def detalle_proveedor(request, proveedor_id):
    with tenant_context(request.tenant):
        proveedor = get_object_or_404(Proveedor, id=proveedor_id, empresa=request.tenant)
        context = {'proveedor': proveedor}
        return render(request, 'proveedores/detalle_proveedor.html', context)


def lista_proveedores(request):
    with tenant_context(request.tenant):  # Asegura que los proveedores se asocian al tenant actual
        proveedores = Proveedor.objects.all()  # Obtiene todos los proveedores asociados al tenant actual
    return render(request, 'proveedores/lista_proveedores.html', {'proveedores': proveedores})



def lista_compras(request):
    with tenant_context(request.tenant):
        compras = Compra.objects.all()  # Se asegura de obtener solo las compras del tenant actual
    return render(request, 'compras/lista_compras.html', {'compras': compras})

def crear_compra_con_productos(request):
    with tenant_context(request.tenant):
        DetalleCompraFormSet = inlineformset_factory(
            Compra, DetalleCompra, form=DetalleCompraForm, extra=1
        )

        impuesto_activo = Impuesto.objects.filter(activo=True).first()
        if not impuesto_activo:
            raise ValidationError("No hay un impuesto activo definido.")

        if request.method == 'POST':
            compra_form = CompraForm(request.POST)
            formset = DetalleCompraFormSet(request.POST, prefix='detalles')

            if compra_form.is_valid() and formset.is_valid():
                compra = compra_form.save(commit=False)
                compra.total_sin_impuestos = Decimal('0.00')
                compra.total_con_impuestos = Decimal('0.00')
                compra.save()

                total_sin_impuestos = Decimal('0.00')
                total_con_impuestos = Decimal('0.00')

                detalles = formset.save(commit=False)
                for detalle in detalles:
                    detalle.compra = compra

                    precio_unitario = Decimal(str(detalle.precio_unitario))
                    cantidad = Decimal(str(detalle.cantidad))

                    total_linea_sin_impuesto = precio_unitario * cantidad
                    total_linea_con_impuesto = total_linea_sin_impuesto + (
                        total_linea_sin_impuesto * (Decimal(str(impuesto_activo.porcentaje)) / Decimal('100'))
                    )

                    total_sin_impuestos += total_linea_sin_impuesto
                    total_con_impuestos += total_linea_con_impuesto

                    detalle.save()

                compra.total_sin_impuestos = total_sin_impuestos.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                compra.total_con_impuestos = total_con_impuestos.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                compra.save()

                return redirect('compras:lista_compras')
            else:
                print('Errores en compra_form:', compra_form.errors)
                print('Errores en formset:')
                for form in formset:
                    print(form.errors)
        else:
            compra_form = CompraForm()
            formset = DetalleCompraFormSet(prefix='detalles')

    return render(request, 'compras/crear_compra_con_productos.html', {
        'compra_form': compra_form,
        'formset': formset,
        'impuesto_activo': impuesto_activo.porcentaje,
    })


def detalle_compra(request, compra_id):
    compra = get_object_or_404(Compra, pk=compra_id)
    with tenant_context(compra.sucursal.empresa):
        detalles = compra.detalles.all()
    return render(request, 'compras/detalle_compra.html', {'compra': compra, 'detalles': detalles})




def procesar_compra_xml(request):
    tenant = request.tenant  # Obtener el tenant actual

    with tenant_context(tenant):  # Asegurar que todas las consultas se hagan dentro del esquema correcto
        if request.method == 'POST':
            form = CompraXMLForm(request.POST, request.FILES)
            if form.is_valid():
                sucursal = get_object_or_404(Sucursal, id=form.cleaned_data['sucursal'].id, empresa=tenant)  # Filtrar por tenant
                archivo_xml = request.FILES['archivo_xml']

                # Leer el archivo XML
                tree = ET.parse(archivo_xml)
                root = tree.getroot()

                # Obtener información del proveedor
                razon_social_element = root.find('.//razonSocial')
                razon_social = razon_social_element.text if razon_social_element is not None else "Sin razón social"

                ruc_element = root.find('.//ruc')
                ruc = ruc_element.text if ruc_element is not None else "0000000000"

                proveedor, created = Proveedor.objects.get_or_create(
                    nombre=razon_social,
                    ruc=ruc,
                    empresa=tenant  # 🔹 Asociar proveedor al tenant actual
                )

                # Obtener la fecha de emisión o usar la fecha actual
                fecha_emision_element = root.find('.//fechaEmision')
                fecha_emision = fecha_emision_element.text if fecha_emision_element is not None else timezone.now().date()

                # Obtener los totales de la compra
                total_sin_impuestos_element = root.find('.//totalSinImpuestos')
                total_sin_impuestos = float(total_sin_impuestos_element.text) if total_sin_impuestos_element is not None else 0.0

                total_con_impuestos_element = root.find('.//importeTotal')
                total_con_impuestos = float(total_con_impuestos_element.text) if total_con_impuestos_element is not None else 0.0

                # Crear la compra (una sola compra para varios productos)
                compra = Compra.objects.create(
                    proveedor=proveedor,
                    sucursal=sucursal,
                    fecha_emision=fecha_emision,
                    total_sin_impuestos=total_sin_impuestos,
                    total_con_impuestos=total_con_impuestos,
                    empresa=tenant  # 🔹 Asociar la compra con el tenant actual
                )

                # Procesar los productos y agregarlos a la compra
                errores = []
                for detalle in root.findall('.//detalle'):
                    # Extraer valores del producto
                    codigo_producto_element = detalle.find('codigoPrincipal')
                    codigo_producto = codigo_producto_element.text if codigo_producto_element is not None else "Sin código"

                    descripcion_element = detalle.find('descripcion')
                    descripcion = descripcion_element.text if descripcion_element is not None else "Sin descripción"

                    cantidad_element = detalle.find('cantidad')
                    cantidad = float(cantidad_element.text) if cantidad_element is not None else 0

                    precio_unitario_element = detalle.find('precioUnitario')
                    precio_unitario = float(precio_unitario_element.text) if precio_unitario_element is not None else 0.0

                    precio_total_sin_impuesto_element = detalle.find('precioTotalSinImpuesto')
                    precio_total_sin_impuesto = float(precio_total_sin_impuesto_element.text) if precio_total_sin_impuesto_element is not None else 0.0

                    descuento_element = detalle.find('descuento')
                    descuento = float(descuento_element.text) if descuento_element is not None else 0.0

                    # Buscar o crear el producto en el tenant actual
                    producto, created = Producto.objects.get_or_create(
                        codigo=codigo_producto,
                        nombre=descripcion,
                        empresa=tenant  # 🔹 Filtrar productos por tenant
                    )

                    # Crear el detalle de compra
                    DetalleCompra.objects.create(
                        compra=compra,
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario,
                        total_por_producto=precio_total_sin_impuesto - descuento,
                        empresa=tenant  # 🔹 Asociar detalle con el tenant actual
                    )

                    print(f"Producto {codigo_producto} procesado: {cantidad} unidades a {precio_unitario} cada una.")

                print("Compra procesada exitosamente.")
                return redirect('compras:lista_compras')
            else:
                print("Formulario no es válido:", form.errors)

        else:
            form = CompraXMLForm()

    return render(request, 'compras/subir_xml.html', {'form': form})