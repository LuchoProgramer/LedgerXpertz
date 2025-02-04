from django import forms
from core.models import Producto, Presentacion
from inventarios.models import Inventario
from .models import CierreCaja
from inventarios.services.validacion_inventario_service import ValidacionInventarioService
from django_tenants.utils import tenant_context

class CierreCajaForm(forms.ModelForm):
    class Meta:
        model = CierreCaja
        fields = ['efectivo_total', 'tarjeta_total', 'transferencia_total', 'salidas_caja', 'motivo_salida']  # Añadido motivo_salida

        widgets = {
            'efectivo_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'tarjeta_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'transferencia_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'salidas_caja': forms.NumberInput(attrs={'class': 'form-control'}),
            'motivo_salida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Motivo de la salida de caja'}),  # Widget para motivo_salida
        }

class SeleccionVentaForm(forms.Form):
    producto = forms.ModelChoiceField(queryset=Producto.objects.none(), label="Producto", empty_label="Seleccione un producto")
    presentacion = forms.ModelChoiceField(queryset=Presentacion.objects.none(), label="Presentación", empty_label="Seleccione una presentación")
    cantidad = forms.IntegerField(min_value=1, label="Cantidad")
    
    def __init__(self, *args, **kwargs):
        sucursal_id = kwargs.pop('sucursal_id', None)
        self.sucursal_id = sucursal_id
        super().__init__(*args, **kwargs)
        
        if sucursal_id:
            # Usamos tenant_context para garantizar que las consultas se realicen dentro del contexto del tenant
            with tenant_context(self.sucursal_id):
                productos_disponibles = Producto.objects.filter(inventario__sucursal_id=sucursal_id)
                if not productos_disponibles.exists():
                    self.fields['producto'].empty_label = "No hay productos disponibles"
                self.fields['producto'].queryset = productos_disponibles

        # Si hay un producto seleccionado, cargamos las presentaciones correspondientes
        if 'producto' in self.data:
            try:
                producto_id = int(self.data.get('producto'))
                # Usamos tenant_context para cargar las presentaciones dentro del contexto del tenant
                with tenant_context(self.sucursal_id):
                    self.fields['presentacion'].queryset = Presentacion.objects.filter(producto_id=producto_id)
            except (ValueError, TypeError):
                self.fields['presentacion'].queryset = Presentacion.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        producto = cleaned_data.get("producto")
        presentacion = cleaned_data.get("presentacion")
        cantidad = cleaned_data.get("cantidad")
        sucursal_id = self.initial.get('sucursal_id')

        if producto and presentacion and sucursal_id and cantidad:
            # Usar el servicio especializado de validación de inventario dentro del tenant context
            with tenant_context(sucursal_id):
                if not ValidacionInventarioService.validar_inventario(producto, presentacion, cantidad):
                    raise forms.ValidationError(f"No hay suficiente stock disponible para {producto.nombre} en la sucursal seleccionada.")
        return cleaned_data

class MetodoPagoForm(forms.Form):
    METODOS_PAGO_SRI = [
        ('01', 'Sin utilización del sistema financiero'),
        ('15', 'Compensación de deudas'),
        ('16', 'Tarjeta de débito'),
        ('17', 'Dinero electrónico'),
        ('18', 'Tarjeta prepago'),
        ('19', 'Tarjeta de crédito'),
        ('20', 'Otros con utilización del sistema financiero'),
        ('21', 'Endoso de títulos'),
    ]
    metodo_pago = forms.ChoiceField(choices=METODOS_PAGO_SRI, label="Método de Pago")