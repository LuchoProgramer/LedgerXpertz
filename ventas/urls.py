# urls.py

from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    path('registrar-venta/', views.registrar_venta, name='registrar_venta'),
    path('inicio-turno/<int:turno_id>/', views.inicio_turno, name='inicio_turno'),
    path('agregar-al-carrito/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('ver-carrito/', views.ver_carrito, name='ver_carrito'),
    path('eliminar-item-carrito/', views.eliminar_item_carrito, name='eliminar_item_carrito'),
    path('actualizar-cantidad-carrito/', views.actualizar_cantidad_carrito, name='actualizar_cantidad_carrito'),
    path('cerrar_turno/', views.cerrar_turno, name='cerrar_turno'),
]