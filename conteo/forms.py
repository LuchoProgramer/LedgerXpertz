from django import forms
from .models import ConteoDiario
from core.models import Producto, Categoria

class ConteoProductoForm(forms.Form):
    # Filtro por categoría, opcional para filtrar productos por categoría
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(),
        required=False,
        empty_label="Todas las Categorías",
        label="Filtrar por Categoría",
        widget=forms.Select(attrs={
            'id': 'categoria-select',
            'class': 'form-control'
        })
    )

    def __init__(self, *args, **kwargs):
        # Obtener los productos de la sucursal que se pasa como parámetro
        productos = kwargs.pop('productos')
        super().__init__(*args, **kwargs)
        self.productos = productos  # Guardamos los productos para usarlos en la validación

        # Crear dinámicamente los campos de cantidad para cada producto
        for producto in productos:
            field_name = f'cantidad_{producto.id}'
            self.fields[field_name] = forms.IntegerField(
                required=False,
                min_value=0,
                label=producto.nombre,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Cantidad',
                    'type': 'number',
                    'min': '0'
                })
            )

    def clean(self):
        cleaned_data = super().clean()

        # Validar que las cantidades no sean negativas
        for producto in self.productos:
            field_name = f'cantidad_{producto.id}'
            cantidad = cleaned_data.get(field_name)

            if cantidad is not None:
                if cantidad < 0:
                    self.add_error(field_name, f'La cantidad para {producto.nombre} no puede ser negativa.')

        return cleaned_data