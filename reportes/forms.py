from django import forms
from core.models import Sucursal
from django.contrib.auth.models import User
from RegistroTurnos.models import RegistroTurno

class FiltroReporteVentasForm(forms.Form):
    sucursal = forms.ModelChoiceField(queryset=Sucursal.objects.none(), required=False)
    fecha_inicio = forms.DateField(widget=forms.SelectDateWidget(), required=False)
    fecha_fin = forms.DateField(widget=forms.SelectDateWidget(), required=False)
    usuario = forms.ModelChoiceField(queryset=User.objects.none(), required=False)
    turno = forms.ModelChoiceField(queryset=RegistroTurno.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        # Se espera que el tenant sea pasado como un parámetro adicional al formulario
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)

        if tenant:
            # Filtrar los querysets basados en el tenant actual
            self.fields['sucursal'].queryset = Sucursal.objects.filter(tenant=tenant)
            self.fields['usuario'].queryset = User.objects.filter(tenant=tenant)
            self.fields['turno'].queryset = RegistroTurno.objects.filter(tenant=tenant)
