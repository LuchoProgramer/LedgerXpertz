from django import forms
from .models import Sucursal, Producto, Categoria,Presentacion
from django.contrib.auth.models import User
from django.forms import inlineformset_factory, BaseInlineFormSet



class SucursalForm(forms.ModelForm):
    usuarios = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Sucursal
        fields = ['nombre', 'direccion', 'telefono', 'codigo_establecimiento', 'punto_emision', 'es_matriz', 'usuarios']
        widgets = {
            'direccion': forms.Textarea(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_establecimiento': forms.TextInput(attrs={'class': 'form-control'}),
            'punto_emision': forms.TextInput(attrs={'class': 'form-control'}),
            'es_matriz': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa 
        if empresa:  # Asignar empresa a la instancia si se proporciona
            self.instance.empresa = empresa 

    def save(self, commit=True):
        print(f"Antes de super().save(): {self}")  # Imprimir el formulario
        instance = super().save(commit=False)  # Crear la instancia
        print(f"Después de super().save(): {instance}") 
        print(f"Valor de self.empresa antes de asignar: {instance.empresa}") 
        instance.empresa = self.empresa 
        print(f"Valor de instance.empresa después de asignar: {instance.empresa}") 
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ProductoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None) 
        super().__init__(*args, **kwargs)
        if self.empresa:
            self.fields['categoria'].queryset = Categoria.objects.filter(empresa=self.empresa)
            self.fields['sucursales'].queryset = Sucursal.objects.filter(empresa=self.empresa)

    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'unidad_medida', 'categoria',
            'sucursales', 'codigo_producto', 'impuesto', 'image'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'sucursales': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'codigo_producto': forms.TextInput(attrs={'class': 'form-control'}),
            'impuesto': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_codigo_producto(self):
        codigo = self.cleaned_data.get('codigo_producto')
        if Producto.objects.filter(codigo_producto=codigo, empresa=self.empresa).exists():
            raise forms.ValidationError(f"El código '{codigo}' ya está en uso para esta empresa.")
        return codigo
    

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']



from django import forms
from .models import Presentacion, Sucursal

class PresentacionForm(forms.ModelForm):
    class Meta:
        model = Presentacion
        fields = ['nombre_presentacion', 'cantidad', 'precio', 'sucursal']

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)  # Extraemos 'tenant' si se pasa
        super().__init__(*args, **kwargs)

        if tenant:
            self.fields['sucursal'].queryset = Sucursal.objects.filter(empresa=tenant)
        else:
            print("⚠ Advertencia: No se pasó el 'tenant' al formulario PresentacionForm")


class BasePresentacionFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)  # Extraemos 'tenant'
        super().__init__(*args, **kwargs)

    def add_fields(self, form, index):
        """Se ejecuta en cada formulario dentro del FormSet"""
        super().add_fields(form, index)
        if self.tenant:
            form.fields['sucursal'].queryset = Sucursal.objects.filter(empresa=self.tenant)  # Filtramos por empresa


PresentacionFormSet = inlineformset_factory(
    Producto,
    Presentacion,
    form=PresentacionForm,
    formset=BasePresentacionFormSet,  # Usamos nuestra clase Base
    extra=1,
    fields=['nombre_presentacion', 'cantidad', 'precio', 'sucursal']
)
