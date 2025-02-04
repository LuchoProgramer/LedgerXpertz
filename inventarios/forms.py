from django import forms
from .models import Transferencia, Inventario
from core.models import Sucursal, Producto
from core.models import Sucursal, Producto



class TransferenciaForm(forms.ModelForm):
    class Meta:
        model = Transferencia
        fields = ['sucursal_origen', 'sucursal_destino', 'producto', 'cantidad']

    def __init__(self, *args, tenant=None, **kwargs):  # 🔹 Extraemos `tenant` antes de llamar a super()
        if 'tenant' in kwargs:
            tenant = kwargs.pop('tenant')  # Se extrae `tenant` antes de llamar a `super()`
        super().__init__(*args, **kwargs)

        if tenant:
            # 🔹 Filtrar sucursales por el tenant actual
            self.fields['sucursal_origen'].queryset = Sucursal.objects.filter(empresa=tenant)
            self.fields['sucursal_destino'].queryset = Sucursal.objects.filter(empresa=tenant)

            # 🔹 Filtrar productos por el tenant actual
            self.fields['producto'].queryset = Producto.objects.filter(empresa=tenant)



class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['producto', 'sucursal', 'cantidad']

    def __init__(self, *args, tenant=None, **kwargs):  # 🔹 Se extrae `tenant` antes de llamar a super()
        super().__init__(*args, **kwargs)

        if tenant:
            # Filtrar sucursales por el tenant actual
            self.fields['sucursal'].queryset = Sucursal.objects.filter(empresa=tenant)

            # Filtrar productos por el tenant actual
            self.fields['producto'].queryset = Producto.objects.filter(empresa=tenant)




class UploadFileForm(forms.Form):
    file = forms.FileField(label="Subir archivo Excel")
