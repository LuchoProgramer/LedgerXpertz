from django import forms
from RegistroTurnos.models import RegistroTurno
from core.models import Sucursal
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from django.db import connection
from django_tenants.utils import tenant_context

class RegistroTurnoForm(forms.ModelForm):
    class Meta:
        model = RegistroTurno
        fields = ['sucursal']  # Solo incluir la sucursal

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop('usuario', None)  # Extraer el usuario de kwargs
        super().__init__(*args, **kwargs)
        if usuario:
            current_tenant = connection.tenant
            with tenant_context(current_tenant):  # Asegurar que se usen los datos del tenant activo
                self.fields['sucursal'].queryset = Sucursal.objects.filter(usuarios=usuario)

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Requerido. Introduce una dirección de correo electrónico válida.")
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.none(), required=False, help_text="Selecciona los grupos para este usuario.")  # Inicializamos vacío

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "groups")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_tenant = connection.tenant
        with tenant_context(current_tenant):  # Asegurar que se usen los datos del tenant activo
            self.fields['groups'].queryset = Group.objects.all()  # Actualizamos los grupos disponibles según el tenant

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            current_tenant = connection.tenant
            with tenant_context(current_tenant):  # Aseguramos el contexto del tenant al asignar grupos
                user.groups.set(self.cleaned_data["groups"])  # Asignar los grupos seleccionados al usuario
        return user
