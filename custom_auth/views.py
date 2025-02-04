from django.shortcuts import render
from django.contrib import messages
from .forms import CustomUserCreationForm

def crear_usuario(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # Guardamos el usuario creado
            messages.success(request, f"¡Usuario {user.username} creado exitosamente!")
            return render(request, 'auth/crear_usuario.html', {'form': form})  # Volver a renderizar el formulario con el mensaje de éxito
        else:
            messages.error(request, "Hubo un error en la creación del usuario. Intenta de nuevo.")
    else:
        form = CustomUserCreationForm()

    return render(request, 'auth/crear_usuario.html', {'form': form})