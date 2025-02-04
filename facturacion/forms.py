# forms.py
from django import forms
from .models import Cliente
from .models import Impuesto

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['tipo_identificacion', 'identificacion', 'razon_social', 'direccion', 'telefono', 'email']
        widgets = {
            'tipo_identificacion': forms.Select(attrs={'class': 'form-select'}),
            'identificacion': forms.TextInput(attrs={'class': 'form-control'}),
            'razon_social': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Cliente.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def clean_identificacion(self):
        identificacion = self.cleaned_data.get('identificacion')
        if len(identificacion) < 6:  # Ejemplo de validación de longitud
            raise forms.ValidationError("La identificación debe tener al menos 6 caracteres.")
        return identificacion




class PagoMixtoForm(forms.Form):
    metodo_pago = forms.ChoiceField(
        choices=[('01', 'Sin utilización del sistema financiero'),
                 ('16', 'Tarjeta de débito'),
                 ('19', 'Tarjeta de crédito'),
                 ('20', 'Otros con utilización del sistema financiero')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    monto = forms.DecimalField(
        max_digits=10, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        if monto <= 0:
            raise forms.ValidationError("El monto debe ser un valor positivo.")
        return monto




class ImpuestoForm(forms.ModelForm):
    class Meta:
        model = Impuesto
        fields = ['codigo_impuesto', 'nombre', 'porcentaje', 'activo']
        widgets = {
            'codigo_impuesto': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'porcentaje': forms.NumberInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_porcentaje(self):
        porcentaje = self.cleaned_data.get('porcentaje')
        if porcentaje <= 0:
            raise forms.ValidationError("El porcentaje debe ser mayor que cero.")
        return porcentaje
