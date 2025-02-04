from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group

class CustomUserCreationForm(UserCreationForm):
    # Campos personalizados
    email = forms.EmailField(
        required=True, 
        help_text="Requerido. Introduce una dirección de correo electrónico válida."
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False, 
        help_text="Selecciona los grupos para este usuario."
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "groups")

    def save(self, commit=True):
        """
        Sobrescribimos el método save para agregar el correo electrónico y los grupos
        de usuarios al momento de crear el usuario.
        """
        # Guardamos el usuario sin hacer commit aún para poder modificar sus datos
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]

        # Guardamos el usuario en la base de datos
        if commit:
            user.save()
            # Asignar los grupos seleccionados por el usuario
            user.groups.set(self.cleaned_data["groups"])

        return user