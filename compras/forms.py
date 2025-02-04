from django import forms
from .models import Proveedor, Compra, DetalleCompra
from core.models import Sucursal

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'ruc', 'direccion', 'telefono', 'email', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ruc': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['sucursal', 'proveedor', 'metodo_pago', 'estado', 'fecha_emision', 'total_sin_impuestos', 'total_con_impuestos']
        widgets = {
            'sucursal': forms.Select(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'fecha_emision': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'total_sin_impuestos': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'total_con_impuestos': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)  # Usamos tenant en lugar de empresa
        super(CompraForm, self).__init__(*args, **kwargs)
        if tenant:
            # Filtramos las sucursales y proveedores por el tenant
            self.fields['sucursal'].queryset = Sucursal.objects.filter(empresa__tenant=tenant)
            self.fields['proveedor'].queryset = Proveedor.objects.filter(empresa__tenant=tenant)


class DetalleCompraForm(forms.ModelForm):
    class Meta:
        model = DetalleCompra
        fields = ['producto', 'cantidad', 'precio_unitario']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def clean_precio_unitario(self):
        precio_unitario = self.cleaned_data.get('precio_unitario')

        # Verificar que el precio_unitario no sea nulo o negativo
        if precio_unitario is None or precio_unitario <= 0:
            raise forms.ValidationError("El precio unitario debe ser un número positivo.")

        return precio_unitario
    


class CompraXMLForm(forms.Form):
    sucursal = forms.ModelChoiceField(queryset=Sucursal.objects.none(), label="Sucursal")  # 🔹 Inicialmente vacío
    archivo_xml = forms.FileField(label="Subir archivo XML")

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)

        if tenant:
            # 🔹 Filtrar sucursales para que solo se muestren las del tenant actual
            self.fields['sucursal'].queryset = Sucursal.objects.filter(empresa=tenant)
