# RegistroTurnos/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Ruta para el dashboard donde se registran los turnos
    path('dashboard/', views.dashboard, name='dashboard'),

    # Ruta para cuando el usuario no tiene sucursales asignadas
    path('sin-sucursales/', views.sin_sucursales, name='sin_sucursales'),

    # Puedes agregar otras rutas aquí si es necesario
]
